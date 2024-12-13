from any_charm_base import AnyCharmBase  # type: ignore[import]
from fiveg_core_gnb import FivegCoreGnbProvides, PLMNConfig  # type: ignore[import]
from ops.framework import EventBase, logger
from sdcore_config import SdcoreConfigProvides  # type: ignore[import]

SDCORE_CONFIG_RELATION_NAME = "provide-sdcore-config"
CORE_GNB_RELATION_NAME = "provide-fiveg-core-gnb"


class AnyCharm(AnyCharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sdcore_config = SdcoreConfigProvides(self, SDCORE_CONFIG_RELATION_NAME)
        self._fiveg_core_gnb_provider = FivegCoreGnbProvides(self, CORE_GNB_RELATION_NAME)
        self.framework.observe(
            self.on[SDCORE_CONFIG_RELATION_NAME].relation_changed,
            self.sdcore_config_relation_changed,
        )
        self.framework.observe(
            self.on[CORE_GNB_RELATION_NAME].relation_changed,
            self.fiveg_core_gnb_relation_changed,
        )

    def sdcore_config_relation_changed(self, event: EventBase) -> None:
        sdcore_config_relations = self.model.relations.get(SDCORE_CONFIG_RELATION_NAME)
        if not sdcore_config_relations:
            logger.info("No %s relations found.", SDCORE_CONFIG_RELATION_NAME)
            return
        self._sdcore_config.set_webui_url_in_all_relations(webui_url="sdcore-nms:9876")

    def fiveg_core_gnb_relation_changed(self, event: EventBase):
        core_gnb_relations = self.model.relations.get(CORE_GNB_RELATION_NAME)
        if not core_gnb_relations:
            logger.info("No %s relations found.", CORE_GNB_RELATION_NAME)
            return
        for relation in core_gnb_relations:
            self._fiveg_core_gnb_provider.publish_gnb_config_information(
                relation_id=relation.id,
                tac=1,
                plmns=[PLMNConfig(mcc="001", mnc="01", sst=1, sd=1056816)],
            )
