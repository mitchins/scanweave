//! Duplicate-JSON-key rejection (SPEC Appendix A: "Reject ... duplicate JSON object keys").
//! A bounded byte-level pre-scan run before serde deserialization; serde alone would
//! silently keep the last occurrence.

use crate::error::ScanWeaveError;

const MAX_DEPTH: usize = 256;

struct Scanner<'a> {
    b: &'a [u8],
    i: usize,
}

impl<'a> Scanner<'a> {
    fn ws(&mut self) {
        while self.i < self.b.len() && matches!(self.b[self.i], b' ' | b'\t' | b'\n' | b'\r') {
            self.i += 1;
        }
    }

    fn value(&mut self, depth: usize) -> Result<(), ()> {
        if depth > MAX_DEPTH {
            return Err(());
        }
        self.ws();
        match self.b.get(self.i) {
            Some(b'{') => self.object(depth),
            Some(b'[') => self.array(depth),
            Some(b'"') => self.string().map(|_| ()),
            Some(_) => self.literal(),
            None => Err(()),
        }
    }

    fn object(&mut self, depth: usize) -> Result<(), ()> {
        self.i += 1; // consume '{'
        let mut keys: Vec<String> = Vec::new();
        self.ws();
        if self.b.get(self.i) == Some(&b'}') {
            self.i += 1;
            return Ok(());
        }
        loop {
            self.ws();
            if self.b.get(self.i) != Some(&b'"') {
                return Err(());
            }
            let key = self.string()?;
            if keys.iter().any(|k| k == &key) {
                return Err(());
            }
            keys.push(key);
            self.ws();
            if self.b.get(self.i) != Some(&b':') {
                return Err(());
            }
            self.i += 1;
            self.value(depth + 1)?;
            self.ws();
            match self.b.get(self.i) {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b'}') => {
                    self.i += 1;
                    return Ok(());
                }
                _ => return Err(()),
            }
        }
    }

    fn array(&mut self, depth: usize) -> Result<(), ()> {
        self.i += 1; // consume '['
        self.ws();
        if self.b.get(self.i) == Some(&b']') {
            self.i += 1;
            return Ok(());
        }
        loop {
            self.value(depth + 1)?;
            self.ws();
            match self.b.get(self.i) {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b']') => {
                    self.i += 1;
                    return Ok(());
                }
                _ => return Err(()),
            }
        }
    }

    fn string(&mut self) -> Result<String, ()> {
        self.i += 1; // consume '"'
        let start = self.i;
        let out = String::new();
        while self.i < self.b.len() {
            match self.b[self.i] {
                b'"' => {
                    let raw = &self.b[start..self.i];
                    self.i += 1;
                    if out.is_empty() {
                        // fast path: raw ASCII slice
                        if let Ok(s) = std::str::from_utf8(raw) {
                            return Ok(s.to_string());
                        }
                    }
                    // slow path: rebuild from raw incl. escapes
                    return rebuild_string(raw);
                }
                b'\\' => {
                    // copy segment then handle escape below via rebuild at end;
                    // still validate escape sequence shape now
                    if self.i + 1 >= self.b.len() {
                        return Err(());
                    }
                    match self.b[self.i + 1] {
                        b'"' | b'\\' | b'/' | b'b' | b'f' | b'n' | b'r' | b't' => self.i += 2,
                        b'u' => {
                            if self.i + 6 > self.b.len() {
                                return Err(());
                            }
                            let hex = &self.b[self.i + 2..self.i + 6];
                            if !hex.iter().all(|c| c.is_ascii_hexdigit()) {
                                return Err(());
                            }
                            self.i += 6;
                        }
                        _ => return Err(()),
                    }
                }
                0x00..=0x1F => return Err(()),
                _ => self.i += 1,
            }
        }
        Err(())
    }

    fn literal(&mut self) -> Result<(), ()> {
        let start = self.i;
        while self.i < self.b.len()
            && !matches!(self.b[self.i], b',' | b']' | b'}' | b' ' | b'\t' | b'\n' | b'\r')
        {
            self.i += 1;
        }
        let lit = &self.b[start..self.i];
        // JSON grammar subset for literals/numbers; NaN/Infinity are rejected here and
        // serde_json would also reject them downstream.
        let ok = matches!(lit, b"true" | b"false" | b"null")
            || (!lit.is_empty() && lit[0] == b'-' && lit.len() > 1)
            || (!lit.is_empty() && lit[0].is_ascii_digit());
        if !ok {
            return Err(());
        }
        if lit[0].is_ascii_digit() || (lit[0] == b'-' && lit.len() > 1) {
            return validate_number(lit);
        }
        Ok(())
    }
}

fn validate_number(lit: &[u8]) -> Result<(), ()> {
    let s = std::str::from_utf8(lit).map_err(|_| ())?;
    let mut chars = s.chars().peekable();
    if chars.peek() == Some(&'-') {
        chars.next();
    }
    let mut saw_int = false;
    while let Some(&c) = chars.peek() {
        if c.is_ascii_digit() {
            saw_int = true;
            chars.next();
        } else {
            break;
        }
    }
    if !saw_int {
        return Err(());
    }
    if chars.peek() == Some(&'.') {
        chars.next();
        let mut frac = false;
        while let Some(&c) = chars.peek() {
            if c.is_ascii_digit() {
                frac = true;
                chars.next();
            } else {
                break;
            }
        }
        if !frac {
            return Err(());
        }
    }
    if matches!(chars.peek(), Some('e') | Some('E')) {
        chars.next();
        if matches!(chars.peek(), Some('+') | Some('-')) {
            chars.next();
        }
        let mut exp = false;
        while let Some(&c) = chars.peek() {
            if c.is_ascii_digit() {
                exp = true;
                chars.next();
            } else {
                break;
            }
        }
        if !exp {
            return Err(());
        }
    }
    if chars.next().is_some() {
        return Err(());
    }
    Ok(())
}

// The caller owns escape cursor advancement. Keep the existing slice boundaries
// and surrogate arithmetic unchanged; this extraction does not redefine parsing.
fn append_unicode_escape(raw: &[u8], i: &mut usize, out: &mut String) -> Result<(), ()> {
    if *i + 5 >= raw.len() {
        return Err(());
    }
    let hex = std::str::from_utf8(&raw[*i + 1..*i + 5]).map_err(|_| ())?;
    let cp = u32::from_str_radix(hex, 16).map_err(|_| ())?;
    // surrogate pair handling
    if (0xD800..0xDC00).contains(&cp) {
        if raw.get(*i + 6) != Some(&b'\\') || raw.get(*i + 7) != Some(&b'u') {
            return Err(());
        }
        let hex2 = std::str::from_utf8(&raw[*i + 8..*i + 12]).map_err(|_| ())?;
        let lo = u32::from_str_radix(hex2, 16).map_err(|_| ())?;
        if !(0xDC00..0xE000).contains(&lo) {
            return Err(());
        }
        let c = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
        out.push(char::from_u32(c).ok_or(())?);
        *i += 6;
    } else {
        out.push(char::from_u32(cp).ok_or(())?);
    }
    Ok(())
}

fn rebuild_string(raw: &[u8]) -> Result<String, ()> {
    let mut out = String::new();
    let mut i = 0;
    while i < raw.len() {
        if raw[i] == b'\\' {
            i += 1;
            match raw.get(i) {
                Some(b'"') => out.push('"'),
                Some(b'\\') => out.push('\\'),
                Some(b'/') => out.push('/'),
                Some(b'b') => out.push('\u{8}'),
                Some(b'f') => out.push('\u{c}'),
                Some(b'n') => out.push('\n'),
                Some(b'r') => out.push('\r'),
                Some(b't') => out.push('\t'),
                Some(b'u') => {
                    append_unicode_escape(raw, &mut i, &mut out)?;
                }
                _ => return Err(()),
            }
            i += 1;
        } else {
            let start = i;
            while i < raw.len() && raw[i] != b'\\' {
                i += 1;
            }
            out.push_str(std::str::from_utf8(&raw[start..i]).map_err(|_| ())?);
        }
    }
    Ok(out)
}

/// Pre-scan JSON bytes and reject duplicate object keys with a typed InvalidInput.
pub fn assert_no_duplicate_keys(input: &[u8]) -> Result<(), ScanWeaveError> {
    let mut s = Scanner { b: input, i: 0 };
    s.value(0)
        .map_err(|_| ScanWeaveError::InvalidInput {
            context: "malformed JSON or duplicate object keys".into(),
        })?;
    s.ws();
    if s.i != s.b.len() {
        return Err(ScanWeaveError::InvalidInput {
            context: "trailing bytes after JSON document".into(),
        });
    }
    Ok(())
}

#[cfg(test)]
mod escape_tests {
    #[test]
    fn extracted_unicode_branch_preserves_cursor_and_error_boundaries() {
        let mut at = 0;
        let mut out = String::new();
        super::append_unicode_escape(b"u0061x", &mut at, &mut out).unwrap();
        assert_eq!((at, out.as_str()), (0, "a"));
        super::append_unicode_escape(b"uD800x\\uDC00", &mut at, &mut out).unwrap();
        assert_eq!((at, out.as_str()), (6, "a\u{10000}"));
        for raw in [
            &b"u"[..],
            &b"uZZZZx"[..],
            &b"uD800xx"[..],
            &b"uD800x\\u0061"[..],
            &b"uDC00x"[..],
            &b"u\xff000x"[..],
        ] {
            let mut at = 0;
            assert!(super::append_unicode_escape(raw, &mut at, &mut String::new()).is_err());
        }
    }

    #[test]
    fn simple_escape_rebuild_and_malformed_inputs_keep_their_contract() {
        assert_eq!(
            super::rebuild_string(br#"a\n\t\"\\\/"#).unwrap(),
            "a\n\t\"\\/"
        );
        for input in [
            &b"\\"[..],
            &b"\\z"[..],
            &b"\\u"[..],
            &b"\\uZZZZx"[..],
            &b"\xff"[..],
        ] {
            assert!(super::rebuild_string(input).is_err());
        }
        assert!(super::assert_no_duplicate_keys(br#"{"a":1,"a":2}"#).is_err());
        assert!(super::assert_no_duplicate_keys(br#"{"a":"\u0061"}"#).is_ok());
    }
}
