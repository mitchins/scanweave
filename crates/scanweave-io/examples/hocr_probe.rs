fn main() {
    let data = std::fs::read("/tmp/opencode/p09_tess.hocr").unwrap();
    let doc = scanweave_io::hocr::parse_hocr(&data, 900, 520).unwrap();
    println!("words: {}", doc.words.len());
    for w in doc.words.iter().take(3) {
        let fc = w.chars.first().map(|c| (c.text.clone(), c.confidence));
        println!("text={:?} conf={:?} chars={} first={:?}", w.text, w.confidence, w.chars.len(), fc);
    }
    let missing: Vec<&String> = doc.words.iter().filter(|w| w.chars.is_empty()).map(|w| &w.text).collect();
    println!("words without chars: {:?}", missing);
}
