import threading

class AlarmEngine:
    def __init__(self, repository, rules):
        self.lock = threading.Lock()
        self.repository = repository
        self.rules = rules
        self.active = {e['rule']:e['id'] for e in repository.alarms(active=True)}

    @staticmethod
    def matches(rule, sample):
        if rule.condition == 'offline': return sample.quality in ('Offline','Timeout')
        if sample.quality != 'OK' or sample.value is None: return None
        return {'>': lambda:sample.value>rule.threshold, '<': lambda:sample.value<rule.threshold,
                '==':lambda:sample.value==rule.threshold, 'ativo':lambda:bool(sample.value),
                'inativo':lambda:not bool(sample.value)}[rule.condition]()

    def process(self, sample):
        with self.lock: self._process(sample)

    def _process(self, sample):
        for rule in self.rules:
            if not rule.enabled or rule.tag_id != sample.tag_id: continue
            match = self.matches(rule,sample)
            if match is True and rule.id not in self.active:
                self.active[rule.id] = self.repository.alarm_open(rule,sample)
            elif match is False and rule.id in self.active:
                self.repository.alarm_normalize(self.active.pop(rule.id),sample.timestamp)
