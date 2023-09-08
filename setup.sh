# Python dependencies
pip install -r requirements.txt

# Install SWI-Prolog if not yet installed
# TODO
# Build s(CASP)
cd src/scasp
make
cd ../..

# Install nl2logic as local python package
pip install -e .