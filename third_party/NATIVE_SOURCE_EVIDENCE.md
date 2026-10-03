# Supplementary native notices and source evidence

Checked 2026-10-03. **Redistribution clearance remains open.** This supplement
preserves obtainable upstream notices; it does not certify licensing or make
upstream source archives equivalent to a supplier's corresponding-source bundle.

## What is now preserved

`native-source-inventory.json` records the official URLs, independently calculated
SHA-256 and size of four downloaded Qt 6.11.2 archives (qtbase, qtsvg,
qtimageformats, qttranslations), Mesa 11.2.2, LLVM 3.6.2 and PyQt6 6.11.0. All four Qt hashes
match the values published at each archive URL's `.mirrorlist`. Mesa/LLVM were
retrieved from official HTTPS archives; their signatures were not independently
verified. Archives are not committed here or automatically delivered to recipients.

`native-notices/` preserves 162 original files, with individual hashes and sizes.
It includes 46 upstream attribution records for the retained Qt Core, GUI,
Network, SVG and Image Formats modules, referenced component-specific notices,
applicable license texts, FreeType's full FTL/GPL alternatives, and source metadata.
These are a **candidate notice set for retained modules**, not assertions that
all optional bundled implementations were selected by the supplier. Known
macOS/Android/WebAssembly/ARM-only records, unrelated modules, examples and tests
are excluded. No PDFium/Qt PDF notice set is claimed: this supplement targets the
variant removing qpdf.dll and Qt6Pdf.dll after import checks, not old artifacts.

Qt license alternatives remain alternatives. Including a text does not select
that license on behalf of a distributor. This software uses the FreeType project
where the bundled FreeType implementation is present. Qt translations' original
`licenseRule.json` declares the default module/plugin alternatives; the original
editable `.ts` files remain in the verified qttranslations archive. Compiled `.qm`
file correspondence and supplier translation build options remain to be completed.

The original PyQt6 `pyproject.toml` is also preserved: it specifies SIP >=6.15,<7
and PyQt-builder >=1.19,<2 with backend `sipbuild.api`. Those upstream ranges
are not evidence of the generator versions actually used for the pinned wheel.

## Public Suffix List: verified source-to-binary data chain

This component is stronger than a version inference:

1. Qt's source attribution identifies revision
   `e452c7058d6946bd76952b128c12f5ce87a5acb8` (2026-05-14) of the Public Suffix List.
2. The original editable list was downloaded from that exact upstream revision
   and is included under `native-notices/publicsuffix-e452c7058d6946bd76952b128c12f5ce87a5acb8/`.
3. The included original Qt `psl-make-dafsa` script regenerates Qt's `psl_data.cpp`
   **byte-for-byte**, SHA-256
   `a062699453700cf0744f3c20a0d47618c9223841b69bf7b4a4620e19fda9b679`.
4. Its full 56,135-byte array occurs exactly once, at file offset 1,211,392,
   in the retained Qt6Network.dll from artifact 11257628538 / run 37079239165.
   The manifest records the DLL and array hashes. This is a static byte comparison,
   not a Windows execution or proof of every other Network component.

The list's MPL-2.0 text, libpsl's Chromium BSD notice and generator are preserved
beside the source attribution. Recipients can modify the included editable list
and run the generator; the source URL is recorded in the inventory. The test
`test_native_notice_evidence.py` independently repeats source regeneration.

## Mesa and LLVM

The existing binary comparison identifies opengl32sw.dll as Qt's official signed
Mesa 11.2.2 archive, with an embedded LLVM 3.6.2 version string. This supplement
preserves Mesa's original `docs/license.html` and `docs/COPYING`, plus LLVM's
release license, Support notices and ARM contribution notice. The Mesa source
license page describes the main library as MIT, but explicitly directs readers
to individual source files; `docs/COPYING` includes LGPLv2 text. Merely seeing that
file does **not** prove the Windows DLL includes LGPL components. Conversely,
core MIT wording does not prove every linked component is permissive.

Full component/build mapping, any patches, all applicable source-file notices,
and any resulting source obligations still need resolution. The newer Qt wiki
recipe for Mesa 17.2.2/LLVM 5.0 does not establish this old binary's build recipe.
No claim of complete Mesa/LLVM notices or source correspondence is made.

## Microsoft runtime evidence is separate

`microsoft-runtime-resources.json` records PE version resources and SHA-256 for
**nine** runtime paths in the inspected artifact:

- Five Qt-local MSVCP140{,_1,_2}/VCRUNTIME140{,_1} files: 14.44.35211.0.
- Two root VCRUNTIME140{,_1} files: 14.42.34438.0.
- One MSVCP140 copy each under numpy.libs and pandas.libs: 14.40.33810.0;
  both copies have identical bytes.

Embedded copyright: © Microsoft Corporation. All rights reserved. Version
resources identify files but do not independently authenticate their signatures
or establish the distributor's entitlement. Microsoft states redistribution of
runtime packages and individual binaries is subject to its Visual Studio terms
and limited to licensed Visual Studio users. The maintainer must establish the
applicable supplier/redistribution terms and entitlement for all nine paths.
Microsoft runtime source is not to be requested under Qt's LGPL.

Official references (read-only, no terms accepted):
- https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170

## Remaining release gates

- Obtain supplier configuration, exact toolchain/generator versions, patches and
  corresponding sources for retained Qt/PyQt; or build them from archived source
  with a documented, tested recipe. Wheel hashes alone cannot settle this.
- Reconcile this candidate notice set against the actual retained implementations,
  including complete Mesa/LLVM component notices and Microsoft rights above.
- Establish a durable recipient-facing source delivery location and instructions
  for every released binary, including editable Qt translations. Upstream URLs
  and ephemeral CI downloads alone do not establish the whole obligation.
- Rerun native manifest/notice checks and Windows smoke on the final integrated
  revision. Evidence here describes the named inspected artifact only.

The existing spec copies the complete `third_party` directory. These notices and
the small verified PSL source therefore enter future packages without a spec
change. Their inclusion does not close the remaining gates or authorize release.
