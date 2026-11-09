"""Build a completely local, no-server, one-file website from source-derived JS data."""
from pathlib import Path
from .ingest import ROOT

def main():
    site=ROOT/'site';html=(site/'index.html').read_text()
    css=(site/'assets/styles.css').read_text();js=(site/'assets/app.js').read_text()
    bootstrap=(site/'data/bootstrap.js').read_text()
    focus=(site/'data/focus.js').read_text()
    html=html.replace('<link rel="stylesheet" href="assets/styles.css"/>','<style>'+css+'</style>')
    html=html.replace('<script src="data/bootstrap.js"></script>','<script>'+bootstrap+'</script>')
    html=html.replace('<script src="data/focus.js"></script>','<script>'+focus+'</script>')
    html=html.replace('<script src="assets/app.js"></script>','<script>'+js+'</script>')
    (site/'standalone.html').write_text(html)
    print('Generated fully self-contained',site/'standalone.html')
if __name__=='__main__':main()
