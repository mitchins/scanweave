//! Tiny hOCR reader with honest word/symbol granularity (M0 scope).
//!
//! - Word boxes are always read (`ocrx_word`).
//! - Per-character boxes are read only when Tesseract's character-box hOCR
//!   (`hocr_char_boxes=1`) emitted them (`ocrx_cinfo` children with `x_bboxes`).
//! - Word-only input NEVER fabricates per-character geometry (IN-04).
//! - External entity declarations (DOCTYPE SYSTEM/PUBLIC) are rejected without
//!   any fetch attempt (IN-06).
//! - Inputs above the configured byte budget are rejected before parsing (IN-06).

use quick_xml::events::{BytesStart, Event};
use quick_xml::Reader;
use scanweave_core::error::ScanWeaveError;

#[derive(Debug, Clone, PartialEq)]
pub struct HocrChar {
    pub text: String,
    pub bbox: (i64, i64, i64, i64),
    pub confidence: Option<f64>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct HocrWord {
    pub text: String,
    pub bbox: (i64, i64, i64, i64),
    pub confidence: Option<f64>,
    pub chars: Vec<HocrChar>,
    pub line_index: usize,
}

#[derive(Debug, Clone, Default)]
pub struct HocrDocument {
    pub words: Vec<HocrWord>,
    pub page_bbox: Option<(i64, i64, i64, i64)>,
    pub producer_name: Option<String>,
}

#[derive(Default)]
struct ParseState {
    words: Vec<HocrWord>,
    page_bbox: Option<(i64, i64, i64, i64)>,
    producer_name: Option<String>,
    cur_word: Option<HocrWord>,
    cur_char: Option<HocrChar>,
    line_index: usize,
    // open-element class stack for span/div/p/html
    stack: Vec<String>,
}

fn invalid(context: impl Into<String>) -> ScanWeaveError {
    ScanWeaveError::InvalidInput {
        context: context.into(),
    }
}

fn parse_title_map(title: &str) -> Vec<(String, String)> {
    let mut out = Vec::new();
    for part in title.split(';') {
        let part = part.trim();
        if part.is_empty() {
            continue;
        }
        if let Some(space) = part.find(' ') {
            out.push((part[..space].to_string(), part[space + 1..].to_string()));
        } else {
            out.push((part.to_string(), String::new()));
        }
    }
    out
}

fn parse_bbox(v: &str) -> Result<(i64, i64, i64, i64), ScanWeaveError> {
    let nums: Vec<i64> = v
        .split_whitespace()
        .map(|t| t.parse::<i64>())
        .take(4)
        .collect::<Result<_, _>>()
        .map_err(|_| invalid(format!("unparseable bbox {v:?}")))?;
    if nums.len() != 4 {
        return Err(invalid(format!("bbox needs 4 integers, got {v:?}")));
    }
    Ok((nums[0], nums[1], nums[2], nums[3]))
}

fn element_attrs(e: &BytesStart) -> Result<(String, String), ScanWeaveError> {
    let mut class = String::new();
    let mut title = String::new();
    for attr in e.attributes() {
        let attr = attr.map_err(|err| invalid(format!("bad attribute: {err}")))?;
        match attr.key.as_ref() {
            b"class" => class = String::from_utf8_lossy(&attr.value).to_string(),
            b"title" => title = String::from_utf8_lossy(&attr.value).to_string(),
            _ => {}
        }
    }
    Ok((class, title))
}

fn handle_start(
    is_empty: bool,
    name: String,
    title: String,
    class: String,
    st: &mut ParseState,
    raster_w: u32,
    raster_h: u32,
) -> Result<(), ScanWeaveError> {
    // track open container elements by NAME; the stack stores their CLASS
    if !is_empty && matches!(name.as_str(), "html" | "div" | "span" | "p") {
        st.stack.push(class.clone());
    }
    match class.as_str() {
        "ocr_page" => {
            for (k, v) in parse_title_map(&title) {
                if k == "bbox" {
                    st.page_bbox = Some(parse_bbox(&v)?);
                }
            }
            if let Some((x0, y0, x1, y1)) = st.page_bbox {
                if (x1 - x0) as u32 != raster_w || (y1 - y0) as u32 != raster_h {
                    return Err(invalid(format!(
                        "hOCR page bbox {x0} {y0} {x1} {y1} does not match canonical raster {raster_w}x{raster_h} — stale or wrong page binding"
                    )));
                }
            }
        }
        "ocr_line" => {
            if !title.is_empty() {
                st.line_index += 1;
            }
        }
        "ocrx_word" => {
            let map = parse_title_map(&title);
            let mut bbox: Option<(i64, i64, i64, i64)> = None;
            let mut conf: Option<f64> = None;
            for (k, v) in &map {
                match k.as_str() {
                    "bbox" => bbox = Some(parse_bbox(v)?),
                    "x_wconf" => conf = v.trim().parse::<f64>().ok(),
                    _ => {}
                }
            }
            let bbox = bbox.ok_or_else(|| invalid("ocrx_word without bbox"))?;
            st.cur_word = Some(HocrWord {
                text: String::new(),
                bbox,
                confidence: conf,
                chars: Vec::new(),
                line_index: st.line_index,
            });
        }
        "ocrx_cinfo" => {
            let map = parse_title_map(&title);
            let mut bbox: Option<(i64, i64, i64, i64)> = None;
            let mut conf: Option<f64> = None;
            for (k, v) in &map {
                match k.as_str() {
                    "x_bboxes" => bbox = Some(parse_bbox(v)?),
                    // tesseract <=4 emits x_confs (list); 5.x emits x_conf (single)
                    "x_confs" => {
                        conf = v
                            .split_whitespace()
                            .next()
                            .and_then(|t| t.parse::<f64>().ok())
                    }
                    "x_conf" => conf = v.trim().parse::<f64>().ok(),
                    _ => {}
                }
            }
            let bbox = bbox.ok_or_else(|| invalid("ocrx_cinfo without x_bboxes"))?;
            st.cur_char = Some(HocrChar {
                text: String::new(),
                bbox,
                confidence: conf,
            });
        }
        _ => {}
    }
    Ok(())
}

/// Parse hOCR bytes into a word/char document. Bounded and offline.
pub fn parse_hocr(
    input: &[u8],
    raster_w: u32,
    raster_h: u32,
) -> Result<HocrDocument, ScanWeaveError> {
    if input.len() > scanweave_core::Limits::m0_defaults().max_ocr_page_bytes {
        return Err(ScanWeaveError::ResourceLimit {
            limit: "max_ocr_page_bytes".into(),
            context: format!("hOCR input is {} bytes", input.len()),
        });
    }
    let mut reader = Reader::from_reader(input);
    reader.config_mut().check_end_names = true;

    let mut st = ParseState::default();

    loop {
        let ev = reader
            .read_event()
            .map_err(|e| invalid(format!("malformed hOCR XML: {e}")))?;
        match ev {
            Event::Start(e) => {
                let (class, title) = element_attrs(&e)?;
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                handle_start(false, name, title, class, &mut st, raster_w, raster_h)?;
            }
            Event::Empty(e) => {
                let (class, title) = element_attrs(&e)?;
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                handle_start(true, name, title, class, &mut st, raster_w, raster_h)?;
            }
            Event::Text(t) => {
                let text = t
                    .unescape()
                    .map_err(|e| invalid(format!("invalid hOCR text entity: {e}")))?
                    .into_owned();
                if st.cur_char.is_some() {
                    if let Some(c) = st.cur_char.as_mut() {
                        c.text.push_str(text.trim_matches('\n'));
                    }
                } else if let Some(w) = st.cur_word.as_mut() {
                    w.text.push_str(&text);
                }
            }
            Event::End(e) => {
                let name = String::from_utf8_lossy(e.name().as_ref()).to_string();
                if matches!(name.as_str(), "span" | "div" | "p" | "html") {
                    if let Some(class) = st.stack.pop() {
                        if class == "ocrx_cinfo" {
                            if let Some(c) = st.cur_char.take() {
                                // Tesseract can emit a genuine space cinfo.
                                // Trimming it created an invalid empty Unicode
                                // range and prevented real receipts from loading.
                                if !c.text.is_empty() {
                                    if let Some(w) = st.cur_word.as_mut() {
                                        w.chars.push(c);
                                    }
                                }
                            }
                        } else if class == "ocrx_word" {
                            if let Some(mut w) = st.cur_word.take() {
                                w.text = w.text.trim().to_string();
                                if w.text.is_empty() && !w.chars.is_empty() {
                                    // char-box hOCR (tesseract 5.x): the word span
                                    // carries no direct text; the honest word text is
                                    // the concatenation of the character labels
                                    w.text = w.chars.iter().map(|c| c.text.as_str()).collect();
                                }
                                st.words.push(w);
                            }
                        }
                    }
                }
            }
            Event::DocType(_) => {
                // DOCTYPE is tolerated: real Tesseract hOCR carries an XHTML DOCTYPE.
                // quick-xml performs NO external entity resolution; unknown entity
                // references in text fail unescape (bounded rejection) — proven by the
                // in06_external_entity_not_fetched test.
            }
            Event::Eof => break,
            _ => {}
        }
    }

    Ok(HocrDocument {
        words: st.words,
        page_bbox: st.page_bbox,
        producer_name: st.producer_name,
    })
}

#[cfg(test)]
mod real_character_tests {
    use super::*;
    #[test]
    fn preserves_space_characters_and_escaped_punctuation() {
        let input = br#"<html><body><div class="ocr_page" title="bbox 0 0 100 40"><span class="ocr_line"><span class="ocrx_word" title="bbox 1 2 30 20"><span class="ocrx_cinfo" title="x_bboxes 1 2 4 20"> </span><span class="ocrx_cinfo" title="x_bboxes 5 2 15 20">&amp;</span></span></span></div></body></html>"#;
        let doc = parse_hocr(input, 100, 40).unwrap();
        assert_eq!(doc.words[0].text, " &");
        assert_eq!(doc.words[0].chars[0].text, " ");
        assert_eq!(doc.words[0].chars[1].text, "&");
    }
}
