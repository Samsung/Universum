from .base_server import BaseServerForHostingBuild, BaseServerForTrigger

__all__ = [
    "LocalServer"
]


class LocalServer(BaseServerForHostingBuild, BaseServerForTrigger):

    def report_build_location(self) -> str:
        return "Local build. No external logs provided"

    def artifact_path(self, local_artifacts_dir: str, item: str) -> str:
        return local_artifacts_dir + "/" + item
