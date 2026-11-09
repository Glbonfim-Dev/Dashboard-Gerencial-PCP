"""Publicacao de dados.json pela API REST do GitHub."""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import quote

import requests


class GitHubConfigError(ValueError):
    """Configuracao do GitHub ausente ou invalida."""


class GitHubUploadError(RuntimeError):
    """Falha controlada na publicacao do JSON."""


@dataclass(frozen=True)
class GitHubConfig:
    """Credenciais e destino do arquivo no repositório."""

    token: str
    owner: str
    repo: str
    branch: str = "main"
    json_path: str = "dados.json"

    @property
    def configurado(self) -> bool:
        """Indica se os três campos obrigatórios foram informados."""

        return bool(self.token and self.owner and self.repo)

    def validar(self) -> None:
        """Bloqueia configuração incompleta ou caminho remoto inseguro."""

        if not self.configurado:
            raise GitHubConfigError(
                "GITHUB_TOKEN, GITHUB_OWNER e GITHUB_REPO devem estar configurados"
            )
        path = PurePosixPath(self.json_path)
        if path.is_absolute() or ".." in path.parts:
            raise GitHubConfigError("GITHUB_JSON_PATH deve ser um caminho relativo seguro")


class GitHubClient:
    """Cliente mínimo para criar ou atualizar um arquivo pela API REST."""

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        config: GitHubConfig,
        logger: logging.Logger,
        session: requests.Session | None = None,
    ) -> None:
        config.validar()
        self.config = config
        self.logger = logger
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {config.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "dashboard-gerencial-automacao",
            }
        )

    @property
    def contents_url(self) -> str:
        """Monta a URL codificando proprietário, repositório e caminho."""

        caminho = "/".join(quote(parte, safe="") for parte in PurePosixPath(self.config.json_path).parts)
        return (
            f"{self.API_BASE}/repos/{quote(self.config.owner, safe='')}/"
            f"{quote(self.config.repo, safe='')}/contents/{caminho}"
        )

    def _request_com_retentativa(self, method: str, **kwargs: object) -> requests.Response:
        """Repete somente falhas temporárias de rede, limite ou servidor."""

        esperas = (5, 10)
        ultimo_erro: Exception | None = None
        for tentativa in range(1, 4):
            try:
                resposta = self.session.request(method, timeout=(10, 30), **kwargs)
                if resposta.status_code == 429 or resposta.status_code >= 500:
                    raise requests.HTTPError(
                        f"GitHub respondeu HTTP {resposta.status_code}", response=resposta
                    )
                return resposta
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as erro:
                ultimo_erro = erro
                self.logger.warning(
                    "Falha temporaria no GitHub, tentativa %d/3: %s", tentativa, erro
                )
                if tentativa < 3:
                    espera = esperas[tentativa - 1]
                    self.logger.info("Nova tentativa de upload em %d segundos", espera)
                    time.sleep(espera)
        raise GitHubUploadError(f"GitHub indisponivel apos 3 tentativas: {ultimo_erro}")

    def publicar_json(self, conteudo: bytes) -> None:
        """Consulta o SHA atual e cria ou atualiza dados.json."""

        self.logger.info(
            "Iniciando upload para %s/%s, branch %s, arquivo %s",
            self.config.owner,
            self.config.repo,
            self.config.branch,
            self.config.json_path,
        )
        consulta = self._request_com_retentativa(
            "GET", url=self.contents_url, params={"ref": self.config.branch}
        )

        sha: str | None = None
        # Atualizações exigem o SHA; arquivos novos não possuem esse campo.
        if consulta.status_code == 200:
            resposta_json = consulta.json()
            sha = resposta_json.get("sha")
            self.logger.info("JSON existente localizado no GitHub")
        elif consulta.status_code == 404:
            self.logger.info("JSON ainda nao existe no GitHub; sera criado")
        else:
            raise GitHubUploadError(
                f"falha ao consultar JSON: HTTP {consulta.status_code} - "
                f"{self._mensagem_resposta(consulta)}"
            )

        payload: dict[str, object] = {
            "message": f"Atualização automática dashboard - {datetime.now():%d/%m/%Y %H:%M}",
            "content": base64.b64encode(conteudo).decode("ascii"),
            "branch": self.config.branch,
        }
        if sha:
            payload["sha"] = sha

        envio = self._request_com_retentativa(
            "PUT", url=self.contents_url, json=payload
        )
        if envio.status_code not in (200, 201):
            raise GitHubUploadError(
                f"falha no upload: HTTP {envio.status_code} - {self._mensagem_resposta(envio)}"
            )
        self.logger.info("GitHub respondeu HTTP %d; upload concluido", envio.status_code)

    @staticmethod
    def _mensagem_resposta(resposta: requests.Response) -> str:
        """Extrai uma mensagem curta sem registrar informações sensíveis."""

        try:
            mensagem = resposta.json().get("message", "resposta sem mensagem")
        except ValueError:
            mensagem = resposta.text[:300] or "resposta vazia"
        return str(mensagem)[:300]
