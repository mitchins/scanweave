//! CID allocation per SPEC §6.1 — the encoding allocation key is the four-tuple
//! (visual_glyph_id, semantic_string, writing_mode, required_metrics).
//! Unicode scalar value, CID and GID are never equated. CIDs start at 1
//! (CID 0 is reserved for .notdef).

/// Writing mode component of the allocation key. Vertical is representable now
/// and exercised in M4; the M0 probe fixes Horizontal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WritingMode {
    Horizontal,
    Vertical,
}

/// Required-metrics component of the allocation key. Two occurrences share a
/// CID only when their required metrics match; a metric variant forces a new
/// encoding entry without a schema change.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct MetricsKey {
    pub advance: u16,
    pub units_per_em: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct EncodingKey {
    pub visual_glyph_id: usize,
    pub semantic_string: String,
    pub writing_mode: WritingMode,
    pub required_metrics: MetricsKey,
}

/// Pure CID allocation: identical keys dedup to one CID; mutating ANY of the
/// four components yields a distinct CID (never merged, never reordered).
pub fn allocate_cids(keys: &[EncodingKey]) -> Vec<usize> {
    let mut out = Vec::with_capacity(keys.len());
    let mut map: std::collections::HashMap<EncodingKey, usize> = std::collections::HashMap::new();
    for k in keys {
        let next = map.len() + 1;
        let cid = *map.entry(k.clone()).or_insert(next);
        out.push(cid);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(glyph: usize, s: &str, wm: WritingMode, advance: u16) -> EncodingKey {
        EncodingKey {
            visual_glyph_id: glyph,
            semantic_string: s.to_string(),
            writing_mode: wm,
            required_metrics: MetricsKey { advance, units_per_em: 2048 },
        }
    }

    /// E0: the four-part key's pure-function property — mutating each component
    /// in turn asserts CID separation; identical keys dedup.
    #[test]
    fn e0_four_part_key_property() {
        let base = key(1, "8", WritingMode::Horizontal, 1700);

        // identical key -> identical CID (dedup)
        let cids = allocate_cids(&[base.clone(), base.clone()]);
        assert_eq!(cids, [1, 1], "same key must dedup to one CID");

        // mutate visual_glyph_id -> new CID
        let cids = allocate_cids(&[base.clone(), key(2, "8", WritingMode::Horizontal, 1700)]);
        assert_eq!(cids, [1, 2], "different glyph must not share a CID");

        // mutate semantic_string -> new CID (same glyph, different label)
        let cids = allocate_cids(&[base.clone(), key(1, "6", WritingMode::Horizontal, 1700)]);
        assert_eq!(cids, [1, 2], "same glyph + different string must get a distinct CID");

        // mutate writing_mode -> new CID
        let cids = allocate_cids(&[base.clone(), key(1, "8", WritingMode::Vertical, 1700)]);
        assert_eq!(cids, [1, 2], "writing_mode must participate in the key");

        // mutate required_metrics -> new CID
        let cids = allocate_cids(&[base.clone(), key(1, "8", WritingMode::Horizontal, 1701)]);
        assert_eq!(cids, [1, 2], "required_metrics must participate in the key");

        // CIDs are 1-based and dense over distinct keys
        let cids = allocate_cids(&[
            key(1, "a", WritingMode::Horizontal, 100),
            key(2, "b", WritingMode::Horizontal, 200),
            key(3, "c", WritingMode::Horizontal, 300),
        ]);
        assert_eq!(cids, [1, 2, 3]);
    }
}
