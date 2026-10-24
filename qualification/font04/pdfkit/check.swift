import Foundation
import PDFKit
import AppKit

// swift check.swift OUTPUT_DIRECTORY default.pdf cover-2.0.pdf cover-1.5.pdf
let args = CommandLine.arguments
 guard args.count == 5 else {
    fputs("Usage: swift check.swift OUTPUT_DIRECTORY default.pdf cover-2.0.pdf cover-1.5.pdf\n", stderr)
    exit(2)
}
let output = URL(fileURLWithPath: args[1], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
var reports: [[String: Any]] = []
var baseline: [String] = []
var failed = false
for (index, path) in args.dropFirst(2).enumerated() {
    guard let document = PDFDocument(url: URL(fileURLWithPath: path)) else {
        fputs("Cannot open \(path)\n", stderr); exit(1)
    }
    var texts: [String] = []
    for pageIndex in 0..<document.pageCount {
        guard let page = document.page(at: pageIndex) else { exit(1) }
        texts.append(page.string ?? "")
        let bounds = page.bounds(for: .mediaBox)
        let scale = 300.0 / 72.0
        let width = Int(ceil(bounds.width * scale))
        let height = Int(ceil(bounds.height * scale))
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width,
                pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 4,
                hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                bytesPerRow: 0, bitsPerPixel: 0),
              let context = NSGraphicsContext(bitmapImageRep: bitmap) else { exit(1) }
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = context
        let cg = context.cgContext
        cg.setFillColor(NSColor.white.cgColor)
        cg.fill(CGRect(x: 0, y: 0, width: width, height: height))
        cg.scaleBy(x: scale, y: scale)
        cg.translateBy(x: -bounds.minX, y: -bounds.minY)
        page.draw(with: .mediaBox, to: cg)
        NSGraphicsContext.restoreGraphicsState()
        guard let png = bitmap.representation(using: .png, properties: [:]) else { exit(1) }
        try png.write(to: output.appendingPathComponent("arm-\(index)-page-\(pageIndex).png"))
    }
    if index == 0 { baseline = texts }
    let equal = texts == baseline
    failed = failed || !equal
    try texts.joined(separator: "\u{000C}").write(to: output.appendingPathComponent("arm-\(index).txt"), atomically: true, encoding: .utf8)
    reports.append(["input": path, "pages": document.pageCount,
        "page_text_equal_to_default": equal,
        "document_string_equal_to_joined_page_strings": (document.string ?? "") == texts.joined(),
        "document_string": document.string ?? "", "render_dpi": 300])
}
// Compare document.string separately: PDFKit may insert page separators.
let strings = reports.map { $0["document_string"] as! String }
let documentEqual = strings.allSatisfy { $0 == strings[0] }
failed = failed || !documentEqual
let result: [String: Any] = ["platform": ProcessInfo.processInfo.operatingSystemVersionString,
    "consumer": "Apple PDFKit", "document_string_equal": documentEqual,
    "reports": reports, "pass": !failed,
    "visual_review": "OWNER REQUIRED: compare all page PNGs and dense text crops against matched PDFium controls"]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
try data.write(to: output.appendingPathComponent("report.json"))
exit(failed ? 1 : 0)
