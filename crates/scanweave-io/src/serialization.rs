//! Final representation of our own pdf-writer output, never an input-PDF parser.
//! Read object boundaries from its classic xref (not binary stream delimiters),
//! pack non-stream objects in bounded ObjStm groups, and emit a Flate xref stream.
use std::io::Write;

pub(crate) fn deflate(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut z = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::new(6));
    z.write_all(data).map_err(|e| e.to_string())?;
    z.finish().map_err(|e| e.to_string())
}

pub(crate) fn compact(input: Vec<u8>) -> Result<Vec<u8>, String> {
    fn error() -> String {
        "unexpected internal pdf-writer cross-reference format".into()
    }
    let marker = b"\nstartxref\n";
    let at = input
        .windows(marker.len())
        .rposition(|s| s == marker)
        .ok_or_else(error)?;
    let tail = std::str::from_utf8(&input[at + marker.len()..]).map_err(|_| error())?;
    let xoff: usize = tail
        .lines()
        .next()
        .ok_or_else(error)?
        .parse()
        .map_err(|_| error())?;
    let xref = std::str::from_utf8(input.get(xoff..at).ok_or_else(error)?).map_err(|_| error())?;
    let mut lines = xref.lines();
    if lines.next() != Some("xref") {
        return Err(error());
    }
    let range: Vec<_> = lines.next().ok_or_else(error)?.split_whitespace().collect();
    if range.len() != 2 || range[0] != "0" {
        return Err(error());
    }
    let size: usize = range[1].parse().map_err(|_| error())?;
    let mut objects = Vec::new();
    for id in 0..size {
        let fields: Vec<_> = lines.next().ok_or_else(error)?.split_whitespace().collect();
        if fields.len() != 3 {
            return Err(error());
        }
        if fields[2] == "n" {
            if fields[1] != "00000" {
                return Err(error());
            }
            objects.push((fields[0].parse::<usize>().map_err(|_| error())?, id));
        }
    }
    objects.sort_unstable();
    let trailer = xref.split_once("trailer\n").ok_or_else(error)?.1.trim();
    let trailer = trailer
        .strip_prefix("<<")
        .and_then(|v| v.strip_suffix(">>"))
        .ok_or_else(error)?;
    let trailer = trailer.replace(&format!("/Size {size}"), "");
    let mut output = b"%PDF-1.7\n%\x80\x80\x80\x80\n".to_vec();
    // (type, offset or object-stream number, generation or stream index)
    let mut entries = vec![(0u8, 0u32, 0u16); size];
    entries[0] = (0, 0, 65535);
    let mut pending = Vec::new();
    for (index, &(start, id)) in objects.iter().enumerate() {
        let end = objects.get(index + 1).map_or(xoff, |x| x.0);
        let object = input.get(start..end).ok_or_else(error)?;
        let header = format!("{id} 0 obj\n");
        let body = object.strip_prefix(header.as_bytes()).ok_or_else(error)?;
        let body_end = body
            .windows(6)
            .rposition(|w| w == b"endobj")
            .ok_or_else(error)?;
        let body = &body[..body_end];
        if body.windows(8).any(|w| w == b"\nstream\n") {
            entries[id] = (1, u32::try_from(output.len()).map_err(|_| error())?, 0);
            output.extend_from_slice(object);
        } else {
            pending.push((id, body));
        }
    }
    for group in pending.chunks(100) {
        let stream_id = entries.len();
        let mut header = String::new();
        let mut bodies = Vec::new();
        for (index, &(id, body)) in group.iter().enumerate() {
            header.push_str(&format!("{id} {} ", bodies.len()));
            bodies.extend_from_slice(body);
            bodies.push(b'\n');
            entries[id] = (2, stream_id as u32, index as u16);
        }
        let first = header.len();
        let mut decoded = header.into_bytes();
        decoded.extend(bodies);
        let compressed = deflate(&decoded)?;
        entries.push((1, u32::try_from(output.len()).map_err(|_| error())?, 0));
        write!(output, "{stream_id} 0 obj\n<< /Type /ObjStm /N {} /First {first} /Filter /FlateDecode /Length {} >>\nstream\n", group.len(), compressed.len()).map_err(|e| e.to_string())?;
        output.extend(compressed);
        output.extend(b"\nendstream\nendobj\n");
    }
    let xid = entries.len();
    let xoffset = output.len();
    entries.push((1, u32::try_from(xoffset).map_err(|_| error())?, 0));
    // Rebuild the complete free list, including sparse unused IDs.
    let free: Vec<_> = (1..entries.len()).filter(|&i| entries[i].0 == 0).collect();
    entries[0].1 = free.first().copied().unwrap_or(0) as u32;
    for (index, &id) in free.iter().enumerate() {
        entries[id].1 = free.get(index + 1).copied().unwrap_or(0) as u32;
    }
    let mut data = Vec::new();
    for (kind, a, b) in &entries {
        data.push(*kind);
        data.extend(a.to_be_bytes());
        data.extend(b.to_be_bytes());
    }
    let compressed = deflate(&data)?;
    write!(output, "{xid} 0 obj\n<< {trailer} /Type /XRef /Size {} /W [1 4 2] /Filter /FlateDecode /Length {} >>\nstream\n", entries.len(), compressed.len()).map_err(|e| e.to_string())?;
    output.extend(compressed);
    write!(output, "\nendstream\nendobj\nstartxref\n{xoffset}\n%%EOF\n")
        .map_err(|e| e.to_string())?;
    Ok(output)
}

#[cfg(test)]
mod tests {
    #[test]
    fn deterministic_sparse_objects_and_binary_stream() {
        use pdf_writer::{Pdf, Ref};
        let mut pdf = Pdf::new();
        pdf.catalog(Ref::new(1)).pages(Ref::new(4));
        pdf.pages(Ref::new(4)).count(0);
        pdf.stream(Ref::new(9), b"endobj\nxref\nstream\n\0binary");
        let raw = pdf.finish();
        let packed = super::compact(raw.clone()).unwrap();
        assert_eq!(packed, super::compact(raw).unwrap());
        assert!(packed.windows(7).any(|s| s == b"/ObjStm"));
        assert!(packed.windows(7).any(|s| s == b"/Type /"));
        assert!(super::compact(b"not a PDF".to_vec()).is_err());
    }
    #[test]
    fn xref_free_chain_and_bounded_object_groups() {
        use pdf_writer::{Pdf, Ref};
        use std::io::Read;
        let mut pdf = Pdf::new();
        pdf.catalog(Ref::new(1)).pages(Ref::new(4));
        pdf.pages(Ref::new(4)).count(0);
        for id in 10..215 {
            pdf.indirect(Ref::new(id)).primitive(id);
        }
        let packed = super::compact(pdf.finish()).unwrap();
        let marker = b"\nstartxref\n";
        let tail = packed
            .windows(marker.len())
            .rposition(|x| x == marker)
            .unwrap()
            + marker.len();
        let offset: usize = std::str::from_utf8(&packed[tail..])
            .unwrap()
            .lines()
            .next()
            .unwrap()
            .parse()
            .unwrap();
        let xref = &packed[offset..];
        let first = xref.windows(8).position(|x| x == b"\nstream\n").unwrap() + 8;
        let end = xref.windows(10).rposition(|x| x == b"\nendstream").unwrap();
        let mut bytes = Vec::new();
        flate2::read::ZlibDecoder::new(&xref[first..end])
            .read_to_end(&mut bytes)
            .unwrap();
        let entries: Vec<_> = bytes
            .chunks_exact(7)
            .map(|b| {
                (
                    b[0],
                    u32::from_be_bytes(b[1..5].try_into().unwrap()),
                    u16::from_be_bytes(b[5..7].try_into().unwrap()),
                )
            })
            .collect();
        let mut next = entries[0].1 as usize;
        let mut free = Vec::new();
        while next != 0 {
            assert!(!free.contains(&next));
            free.push(next);
            assert_eq!(entries[next].0, 0);
            next = entries[next].1 as usize;
        }
        assert_eq!(free, vec![2, 3, 5, 6, 7, 8, 9]);
        for (kind, object, index) in entries {
            if kind == 2 {
                assert!((215..218).contains(&object));
                assert!(index < 100);
            }
        }
    }
}
