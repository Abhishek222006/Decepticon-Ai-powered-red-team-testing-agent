from fastapi import FastAPI, HTTPException

from backend.exec import run_recon_nmap

app = FastAPI(title="Decepticon Execution API")


@app.post("/execute/recon")
def execute_recon():
    try:
        result = run_recon_nmap()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Docker is not installed or not in PATH")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    output = result.output
    if result.exit_code != 0 and not output:
        raise HTTPException(status_code=500, detail="Command failed with no output")

    return {
        "type": "terminal",
        "output": output,
    }


@app.post("/run-recon")
def run_recon_compat():
    return execute_recon()
