// Minimal isolate: same pdf-writer Type0/CIDFontType2 path with a known-good font.
use pdf_writer::{Chunk, Content, Finish, Name, Pdf, Ref, Rect, Str};

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
    pdf.catalog(catalog).pages(page_tree);
    pdf.pages(page_tree).kids([page]).count(1);

    let mut ff = pdf.stream(fontfile, &ttf);
    ff.pair(Name(b"Length1"), ttf.len() as i32);
    ff.finish();

    pdf.font_descriptor(descriptor)
        .name(Name(b"Test"))
        .flags(pdf_writer::types::FontFlags::SYMBOLIC)
        .bbox(Rect::new(-100.0, -100.0, 1200.0, 1200.0))
        .italic_angle(0.0)
        .ascent(900.0)
        .descent(-200.0)
        .cap_height(700.0)
        .stem_v(80.0)
        .font_file2(fontfile);

    let mut cid = pdf.cid_font(cidfont);
    cid.subtype(pdf_writer::types::CidFontType::Type2)
        .base_font(Name(b"Test"))
        .system_info(pdf_writer::types::SystemInfo {
            registry: Str(b"Adobe"),
            ordering: Str(b"Identity"),
            supplement: 0,
        })
        .font_descriptor(descriptor)
        .default_width(1000.0);
    // no CIDToGIDMap -> Identity (CID == GID)
    cid.finish();

    let mut type0 = pdf.type0_font(font);
    type0.base_font(Name(b"Test"))
        .encoding_predefined(Name(b"Identity-H"))
        .descendant_font(cidfont);
    type0.finish();

    let mut c = Content::new();
    c.set_fill_rgb(0.0, 0.0, 0.0);
    c.begin_text();
    c.set_font(Name(b"F1"), 48.0);
    c.next_line(50.0, 100.0);
    // DejaVu glyph for '8' — find its GID via cmap? Identity-H maps CID->GID directly;
    // GID for '8' in DejaVuSans-Bold is some index; use a text via ToUnicode-less test:
    // write code = GID of '8'. We compute it with fontTools offline and hardcode via arg.
    let gid: u16 = std::env::args().nth(2).unwrap().parse().unwrap();
    c.show(Str(&[(gid >> 8) as u8, (gid & 0xff) as u8]));
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
    std::fs::write("/tmp/opencode/isolate.pdf", pdf.finish()).unwrap();
    println!("written /tmp/opencode/isolate.pdf");
}
