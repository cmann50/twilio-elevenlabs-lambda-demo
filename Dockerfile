FROM public.ecr.aws/lambda/python:3.10

# Update the system and install the development tools
# I think we only need this for langchain/pandas
# RUN yum update -y && \
#    yum install -y gcc gcc-c++ make

# Install wget and tar
RUN yum update -y && \
    yum install -y wget tar

RUN yum install -y xz

# Download and extract the static FFmpeg build to /usr/local/bin
RUN wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz && \
    tar xJf ffmpeg-git-amd64-static.tar.xz && \
    cd ffmpeg-git-*-amd64-static && \
    cp ffmpeg ffprobe /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# Keep these last to avoid rebuilding the image when the code changes

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Copy all Python files from src directory
COPY src/*.py ${LAMBDA_TASK_ROOT}/

# Install the specified packages
RUN pip install -r requirements.txt

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD  ["lambda_function.handler" ]