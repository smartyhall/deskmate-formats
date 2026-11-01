Private fixtures stay external. Set DOSLAB_ROOT explicitly and follow docs/evidence/README.md. No archival binaries belong here.

E17 fixture-only checks: set DOSLAB_ROOT and run `python -m unittest discover -s tests/private -p test_e17_reuse.py -v`. These assert the preserved application result; they do not enable multi-page production parsing/writing.

E18: set DOSLAB_ROOT and run `python -m unittest discover -s tests/private -p test_e18_variants.py -v`. External E16/E18 and E15 preflight fixtures remain private. No multi-page runtime support is implied.
