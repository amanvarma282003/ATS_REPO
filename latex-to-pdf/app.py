import logging
import os
import shutil
import subprocess
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, PlainTextResponse

app = FastAPI()

logger = logging.getLogger(__name__)


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "input.tex")
        pdf_path = os.path.join(tmpdir, "input.pdf")
        log_path = os.path.join(tmpdir, "latex.log")

        with open(tex_path, "wb") as f:
            f.write(await file.read())

        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "input.tex"],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return PlainTextResponse("❌ Compilation timed out.", status_code=500)

        with open(log_path, "wb") as f:
            f.write(result.stdout)

        logger.debug("[LATEX] Temp dir contents: %s", os.listdir(tmpdir))
        logger.debug("[LATEX] Return code: %s", result.returncode)

        if not os.path.exists(pdf_path):
            with open(log_path, "r", errors="ignore") as f:
                log_content = f.read()
            return PlainTextResponse(
                f"❌ LaTeX compilation failed:\n\n{log_content}", status_code=500
            )

        # ✅ Move PDF out of temp folder before it gets deleted
        final_pdf = "/tmp/output.pdf"
        shutil.copyfile(pdf_path, final_pdf)

    # Once outside the `with` block, tempdir is deleted — but PDF is safe
    return FileResponse(final_pdf, media_type="application/pdf", filename="output.pdf")
