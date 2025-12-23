FROM tempoquestinc/acecast:4.0.2

# Install necessary utilities
RUN dnf install -y \
    wget \
    tar \
    python3.11 \
    python3.11-pip \
    && dnf clean all

# Copy the Miniconda install script into the container
COPY install_miniconda.sh /app/install_miniconda.sh

# Set python3.11 as the default pythn
RUN ln -sf $(which python3.11) /usr/local/bin/python && \
    ln -sf $(which python3.11) /usr/local/bin/python3

# Install dependencies from requirements.txt
COPY requirements.txt /requirements.txt
RUN pip3 install --no-cache-dir -r /requirements.txt

# Copy env file
COPY environment.yml /app/environment.yml

# Make it executable and run it
RUN chmod +x /app/install_miniconda.sh && /app/install_miniconda.sh

# Copy python scripts
COPY max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_OOP_flexible_dbz_t2_args.py max_dbz_1_0_2_detailed_profi_slo_plus_args.py max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_args.py /app/

# Copy iamges
COPY logo_512_39.webp /app/

# Copy your scripts into the container
COPY upload_latest.sh handler.py ftp_download.sh check_output.sh post_processing.sh generate_images.sh upload.sh upload_logs.sh start_cleaner.sh end_cleaner.sh /app/

# Make shell scripts executable
RUN chmod +x /app/upload_latest.sh /app/ftp_download.sh /app/check_output.sh /app/post_processing.sh /app/generate_images.sh /app/upload_logs.sh /app/upload.sh /app/start_cleaner.sh /app/end_cleaner.sh

# Set the working directory
WORKDIR /app

# Run the handler
CMD ["python", "-u", "handler.py"]
