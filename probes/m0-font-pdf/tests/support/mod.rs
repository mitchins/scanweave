//! Decode compressed PDF syntax before asserting graphics/ownership contracts.
//! Hayro is an independent parser already used by the converter's rendering path.
pub fn decoded_syntax(bytes: &[u8]) -> String {
    use hayro::hayro_syntax::{object::Object, Pdf};
    let pdf = Pdf::new(bytes.to_vec()).expect("assembled PDF parses");
    let mut result = String::new();
    for object in pdf.objects() {
        match object {
            Object::Dict(dict) => {
                result.push_str(&String::from_utf8_lossy(dict.data()));
                result.push('\n');
            }
            Object::Stream(stream) => {
                let dict = String::from_utf8_lossy(stream.dict().data());
                if dict.contains("/ObjStm") || dict.contains("/XRef") {
                    continue;
                }
                result.push_str(&dict);
                result.push('\n');
                if !dict.contains("/Subtype /Image") && !dict.contains("/Length1") {
                    let data = stream.decoded().expect("non-image stream decodes");
                    result.push_str(&String::from_utf8_lossy(&data));
                    result.push('\n');
                }
            }
            _ => {}
        }
    }
    result
}
