# Offline Faxback OCR and product dossiers

The resumable OCR worker joins the private Faxback catalog to PDF analyses
marked for OCR in the general archive index. It verifies each source digest,
uses Poppler to render grayscale pages at a configured long edge, and calls
the Windows OCR engine in a separate PowerShell process. The worker runs
under a process-local `RemoteSigned` policy. The initial attempt under the
host's default script policy recorded 120 recognition failures. The rerun
filled those pages and cleared the failures.

```powershell
python tools/archive/faxback_ocr.py FAXBACK.sqlite LIBRARY.sqlite ORIGINALS OCR.sqlite --minimum 10000 --pages 120
```

Use the same private destination to resume a pass. Use a different
`--pixels` or `--language` setting to add a recognition profile. The
source digest, page number, rendering profile and raster digest identify a
page. Separate document rows retain provenance when sources share content.
Successful pages and their FTS rows commit together. Page failures remain
eligible for retry. The databases and OCR text stay in private lab storage.

The profile records the Poppler release, raster settings, OCR language,
Windows build and worker digest. The Windows OCR API used here provides
text lines without per-word confidence or a separately exposed engine
version. First-page metadata checks store exact matches, numeric conflicts
and leading-zero variants beside the source catalog values. A variant may
reflect the printed form of a catalog number or a recognition error. The
original identifier and recognized string remain separately queryable.

On Windows build 10.0.19045 with Poppler 26.07.0 and en-US recognition, the
2,000-pixel pass saved 120 pages. A rerun with a one-page budget skipped
the completed pages and added one page, reaching 121 pages from 104
documents. The 2,400-pixel comparison saved 60 pages from 51 documents.
There were zero outstanding failures across these two profiles. For the
51 comparable first pages, document-number matches went from 48 to 47
(two gained, three lost). The count of pages with any exact catalog match
went from 27 to 26. These checks measure agreement with the indexed
identifiers over this sample. The 2,000-pixel pass remains the default.

The private `faxback-ocr-resume.sqlite` under the campaign evidence root
holds both profiles. Use a parameterized FTS query against `page_text`
and join the matching `rowid` to `page.id`, then join `page.digest` to
`document.digest`. A reference page can expose selected source URL,
catalog ID, relationship and page locator, with OCR search hits retained
in the private index.

## Reviewed product associations

The [reviewed graph seed](../evidence/faxback-product-edges-20261120.json)
pins each association to a numbered source and its digest. The underlying
catalog index also holds title and body mentions. Those search edges need
relationship review before they can support direct product claims.

### Tandy 1000 TL and TL/2

Catalog 250-1601 and 250-1602 identify separate machine editions. Each
has a dedicated Music note with a workflow for creating sampled
instruments through DeskMate Sound. Each also has a separate video mode
reference, which can help select the documented setup for a native
comparison. Retain both edition identities when linking an emulator
configuration or Music recording to the documentation.
[TL Music](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01209.txt) ·
[TL/2 Music](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/01229.txt)

### Sensation! WinMate environments

Catalog 250-1650 has a WinMate door-restoration procedure, a menu inventory
and a Windows driver note. Catalog 250-1651 has a different menu inventory
and a separate guide to creating an icon by adding a program through
Windows Program Manager and returning to WinMate. The two menu inventories
give concrete edition-specific expectations for eventual native tests of
the WinMate tree recovered from the Data Disc.
[250-1650 WinMate options](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02636.txt) ·
[250-1651 WinMate options](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02862.txt) ·
[Program icon procedure](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/02876.txt)

### DeskMate peripherals and integrations

FaxMate 250-3063 has a catalog record, explicit requirements and a
DeskMate-specific installation workflow. Its requirements document lists
MS-DOS 3.1 or later and DeskMate 3.0 or later. The DMP-240 printer, catalog
260-2839, has a separate DeskMate color driver notice. These are two
specific compatibility relationships with different recovery targets,
one for an application distribution and one for a printer driver.
[FaxMate requirements](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/05387.txt) ·
[FaxMate DeskMate usage](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/05390.txt) ·
[DMP-240 DeskMate color driver](http://ftp.oldskool.org/pub/tvdog/tandy1000/faxback/04347.txt)
