import runpod
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def handler(job):
    """Handler function that will be used to process jobs."""
    job_input = job.get("input", {})

    # Set environment variables from job input
    os.environ["FTP_USER"] = job_input.get("ftp_user", "")
    os.environ["FTP_PASS"] = job_input.get("ftp_pass", "")
    os.environ["FTP_HOST"] = job_input.get("ftp_host", "")
    os.environ["FTP_DIR"]  = job_input.get("ftp_dir", "")

    try:
        logging.info(">> Running start_cleaner.sh...")
        subprocess.run(["./start_cleaner.sh"], check=True)
        logging.info("✅ start_cleaner.sh executed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during cleaner.sh: {e}")
        return {"status": "error", "step": "start_cleaner", "details": str(e)}

    try:
        logging.info(">> Running ftp_download.sh...")
        subprocess.run(["./ftp_download.sh"], check=True)
        logging.info("✅ ftp_download.sh executed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during ftp_download.sh: {e}")
        return {"status": "error", "step": "ftp_download", "details": str(e)}

    try:
        logging.info(">> Running run.sh...")
        subprocess.run(["./run.sh"], check=True)
        logging.info("✅ run.sh executed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ CalledProcessError during run.sh: {e}")
        return {"status": "warning", "step": "run.sh", "details": str(e)}
    except Exception as e:
        logging.error(f"❌ Error during run.sh: {e}")
    
    try:
        logging.info(">> Running upload_logs.sh...")
        subprocess.run(["./upload_logs.sh"], check=True)
        logging.info("✅ upload_logs.sh executed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during upload_logs.sh: {e}")
        return {"status": "warning", "step": "upload_logs.sh", "details": str(e)}

    try:
        logging.info(">> Running end_cleaner.sh...")
        subprocess.run(["./end_cleaner.sh"], check=True)
        logging.info("✅ cleaner.sh executed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error during end_cleaner.sh: {e}")
        return {"status": "error", "step": "end_cleaner", "details": str(e)}

    logging.info("🎉 All steps completed successfully.")
    return {"status": "success"}

runpod.serverless.start({"handler": handler})
