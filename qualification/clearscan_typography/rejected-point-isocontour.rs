//! Subpixel coverage contours in the original observation's pixel-edge frame.
//! Binary ownership bounds the evidence footprint; edge locations come from
//! normalized grayscale samples, not from an enlarged thresholded bitmap.
use crate::{glyphs::ContourLayer, units::Unit};
use std::collections::BTreeMap;
type P = [f64; 2];
type Key = (i64, i64);
fn key(p: P) -> Key { ((p[0]*1e7).round() as i64,(p[1]*1e7).round() as i64) }
fn area(p: &[P]) -> f64 { p.iter().zip(p.iter().cycle().skip(1)).map(|(a,b)|a[0]*b[1]-a[1]*b[0]).sum::<f64>()*0.5 }
fn contains(poly: &[P], p: P) -> bool {
    let mut inside=false;
    for (a,b) in poly.iter().zip(poly.iter().cycle().skip(1)) {
        if (a[1]>p[1])!=(b[1]>p[1]) && p[0] < a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1]) { inside=!inside; }
    }
    inside
}
fn spline(poly: &[P]) -> Vec<P> {
    // Arc-length sampling avoids unstable tangents at tiny marching edges.
    let n=poly.len(); let mut lengths=vec![0.0];
    for i in 0..n { lengths.push(lengths[i]+(poly[(i+1)%n][0]-poly[i][0]).hypot(poly[(i+1)%n][1]-poly[i][1])); }
    let total=lengths[n]; let count=(total/0.6).ceil().max(8.0) as usize;
    let mut p=Vec::with_capacity(count);let mut edge=0;
    for i in 0..count {
        let d=total*i as f64/count as f64;
        while edge+1<n && lengths[edge+1]<d {edge+=1;}
        let t=(d-lengths[edge])/(lengths[edge+1]-lengths[edge]).max(1e-9);
        p.push([poly[edge][0]+t*(poly[(edge+1)%n][0]-poly[edge][0]),poly[edge][1]+t*(poly[(edge+1)%n][1]-poly[edge][1])]);
    }
    let mut out=vec![p[0]];
    for i in 0..count {
        let prev=p[(i+count-1)%count];let a=p[i];let b=p[(i+1)%count];let next=p[(i+2)%count];
        out.push([a[0]+(b[0]-prev[0])/6.0,a[1]+(b[1]-prev[1])/6.0]);
        out.push([b[0]-(next[0]-a[0])/6.0,b[1]-(next[1]-a[1])/6.0]);out.push(b);
    }
    out
}
pub(crate) fn layers(unit: &Unit, paper: f64, ink: f64) -> Option<Vec<ContourLayer>> {
    let gray=unit.gray_samples.as_deref()?;let w=unit.crop_w as isize;let h=unit.crop_h as isize;
    if gray.len()!=unit.mask.len() || w<2 || h<2 {return None;}
    let sample=|x:isize,y:isize| -> f64 {
        // Only observations adjacent to owned ink can create an outline. This
        // excludes neighboring punctuation/artwork in the grayscale halo.
        let nearby=(-1..=1).any(|dy|(-1..=1).any(|dx| {let xx=x+dx;let yy=y+dy;xx>=0&&yy>=0&&xx<w&&yy<h&&unit.mask[(yy*w+xx) as usize]}));
        if !nearby {return 0.0;}
        let value=if x>=0&&y>=0&&x<w&&y<h {gray[(y*w+x) as usize]} else if let Some(halo)=unit.gray_halo.as_deref() {halo[((y+2)*(w+4)+x+2) as usize]} else {255};
        ((paper-value as f64)/(paper-ink)).clamp(0.0,1.0)
    };
    let mut segments: Vec<(P,P)>=Vec::new();
    for y in -1..h {for x in -1..w {
        let p=[[x as f64+0.5,y as f64+0.5],[x as f64+1.5,y as f64+0.5],[x as f64+1.5,y as f64+1.5],[x as f64+0.5,y as f64+1.5]];
        let v=[sample(x,y),sample(x+1,y),sample(x+1,y+1),sample(x,y+1)];let mut hits:Vec<(usize,P)>=Vec::new();
        for e in 0..4 {let n=(e+1)%4;if (v[e]>=0.5)!=(v[n]>=0.5) {let t=(0.5-v[e])/(v[n]-v[e]);hits.push((e,[p[e][0]+t*(p[n][0]-p[e][0]),p[e][1]+t*(p[n][1]-p[e][1])]));}}
        if hits.len()==2 {segments.push((hits[0].1,hits[1].1));}
        else if hits.len()==4 {
            let center=v.iter().sum::<f64>()>=2.0;let northwest=v[0]>=0.5;
            let pairs=if center==northwest {[(0,1),(2,3)]} else {[(3,0),(1,2)]};
            for (a,b) in pairs {segments.push((hits[a].1,hits[b].1));}
        }
    }}
    let mut vertices:BTreeMap<Key,Vec<usize>>=BTreeMap::new();
    for (i,(a,b)) in segments.iter().enumerate() {vertices.entry(key(*a)).or_default().push(i);vertices.entry(key(*b)).or_default().push(i);}
    if vertices.values().any(|v|v.len()!=2) {return None;}
    let mut used=vec![false;segments.len()];let mut rings=Vec::new();
    for start in 0..segments.len() {
        if used[start] {continue;}
        let first=segments[start].0;let mut current=first;let mut edge=start;let mut ring=Vec::new();
        for _ in 0..=segments.len() {
            if used[edge] {break;}
            used[edge]=true;ring.push(current);let (a,b)=segments[edge];current=if key(a)==key(current) {b} else {a};
            if key(current)==key(first) {break;}
            edge=*vertices.get(&key(current))?.iter().find(|&&i|!used[i])?;
        }
        if key(current)!=key(first) || ring.len()<3 {return None;}
        if area(&ring).abs()>0.1 {rings.push(ring);}
    }
    let depths:Vec<usize>=rings.iter().enumerate().map(|(i,r)|rings.iter().enumerate().filter(|(j,p)|*j!=i&&contains(p,r[0])).count()).collect();
    let mut output=Vec::new();
    for (i,r) in rings.iter().enumerate() {
        if depths[i]%2!=0 {continue;}
        let holes=rings.iter().enumerate().filter(|(j,h)|depths[*j]==depths[i]+1&&contains(r,h[0])).map(|(_,h)|spline(h)).collect();
        output.push((spline(r),holes));
    }
    (!output.is_empty()).then_some(output)
}
