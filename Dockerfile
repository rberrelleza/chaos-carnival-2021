FROM okteto/python:3

ENV KUBECTL_VERSION 1.18.5
ENV HELM_VERSION 3.5.2
ENV KUSTOMIZE_VERSION 3.9.2

# installing kubectl
RUN curl -sLf --retry 3 -o kubectl https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
    cp kubectl /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl && \
    /usr/local/bin/kubectl version --client=true

# installing helm
RUN curl -sLf --retry 3 -o helm.tar.gz https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz && \
    mkdir -p helm && tar -C helm -xf helm.tar.gz && \
    cp helm/linux-amd64/helm /usr/local/bin/helm && \
    chmod +x /usr/local/bin/helm && \
    /usr/local/bin/helm version

# installing kustomize
RUN curl -sLf --retry 3 -o kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz \
  && tar -xvzf kustomize.tar.gz -C /usr/local/bin \
  && chmod +x /usr/local/bin/kustomize \
  && /usr/local/bin/kustomize version


COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt