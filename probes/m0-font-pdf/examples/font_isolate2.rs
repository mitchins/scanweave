use pdf_writer::{Chunk, Content, Finish, Name, Pdf, Ref, Rect, Str};
use pdf_writer::types::{CidFontType, SystemInfo};

fn main() {
    let ttf = std::fs::read(std::env::args().nth(1).unwrap()).unwrap();
    let mut pdf = Pdf::new();
    pdf.set_version(1, 7);
    let catalog = Ref::new(1);
    let page_tree = Ref::new(2);
    let page = Ref::new(3);
    let content = Ref::new(4);
    let font = Ref::new(5);
    let cidfont = Ref::new(6);
    let descriptor = Ref::new(7);
    let fontfile = Ref::new(8);
    let cid2gid = Ref::new(9);
    let tounicode = Ref::new(10);
    pdf.catalog(catalog).pages(page_tree);
    pdf.pages(page_tree).kids([page]).count(1);

    let mut ff = pdf.stream(fontfile, &ttf);
    ff.pair(Name(b"Length1"), ttf.len() as i32);
    ff.finish();

    pdf.font_descriptor(descriptor)
        .name(Name(b"ScanWeaveM0Probe"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(-13.0, 0.0, 1559.0, 2150.0))
        .italic_angle(0.0)
        .ascent(2150.0)
        .descent(0.0)
        .cap_height(2150.0)
        .stem_v(80.0)
        .font_file2(fontfile);

    let map_bytes = vec![0u8, 0u8, 0u8, 1u8]; // CID0->GID0, CID1->GID1
    pdf.stream(cid2gid, &map_bytes).finish();

    let cmap = "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <0001>\nendcodespacerange\n1 beginbfchar\n<0001> <0036>\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend end\n";
    pdf.stream(tounicode, cmap.as_bytes()).finish();

    let mut cid = pdf.cid_font(cidfont);
    cid.subtype(CidFontType::Type2)
        .base_font(Name(b"ScanWeaveM0Probe"))
        .system_info(SystemInfo { registry: Str(b"Adobe"), ordering: Str(b"Identity"), supplement: 0 })
        .font_descriptor(descriptor)
        .default_width(1000.0)
        .cid_to_gid_map_stream(cid2gid);
    {
        let mut w = cid.widths();
        w.consecutive(1u16, [769.04297f32]);
        w.finish();
    }
    cid.finish();

    let mut type0 = pdf.type0_font(font);
    type0.base_font(Name(b"ScanWeaveM0Probe"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(cidfont)
        .to_unicode(tounicode);
    type0.finish();

    let mut c = Content::new();
    c.set_fill_rgb(0.0, 0.0, 0.0);
    c.begin_text();
    c.set_font(Name(b"F1"), 1.0);
    c.set_text_matrix([21.2, 0.0, 0.0, 16.8, 14.4, 29.0]);
    c.show(Str(&[0x00u8, 0x01u8])); // CID 1 -> GID 1 via map
    c.end_text();
    let bytes = c.finish();
    pdf.stream(content, &bytes).finish();

    let mut p = pdf.page(page);
    p.parent(page_tree)
        .media_box(Rect::new(0.0, 0.0, 300.0, 150.0))
        .contents(content);
    {
        let mut res = p.resources();
        res.fonts().pair(Name(b"F1"), font);
        res.finish();
    }
    p.finish();
    std::fs::write("/tmp/opencode/isolate2.pdf", pdf.finish()).unwrap();
    println!("written");
}
