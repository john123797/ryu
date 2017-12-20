from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib import hub

class testof(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(testof, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._oftest)

    def _oftest(self):
        while True:
            for dp in self.datapaths.values():
                self.send_sketch_stats_request(dp)
            hub.sleep(10)

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.logger.info("Switch %016x use protocol %d",
                         datapath.id, ofproto.OFP_VERSION)
        msg = ev.msg
        
        self.send_get_config_request(datapath)        

    def send_get_config_request(self, datapath):
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPGetConfigRequest(datapath)
        datapath.send_msg(req)

    def send_sketch_stats_request(self, datapath):
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPSketchRequest(datapath)
        datapath.send_msg(req)
 
    @set_ev_cls(ofp_event.EventOFPSketchReply, MAIN_DISPATCHER)
    def desc_sketch_reply_handler(self,ev):
        body=ev.msg.sketch
        self.logger.info('sketch = %s,', body)

    @set_ev_cls(ofp_event.EventOFPGetConfigReply, MAIN_DISPATCHER)
    def get_config_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto

        if msg.flags == ofp.OFPC_FRAG_NORMAL:
            flags = 'NORMAL'
        elif msg.flags == ofp.OFPC_FRAG_DROP:
            flags = 'DROP'
        elif msg.flags == ofp.OFPC_FRAG_REASM:
            flags = 'REASM'
        elif msg.flags == ofp.OFPC_FRAG_MASK:
            flags = 'MASK'
        else:
            flags = 'unknown'
        self.logger.debug('OFPGetConfigReply received: '
                              'flags=%s miss_send_len=%d',
                              flags, msg.miss_send_len)
