from covid.infection.symptoms import Symptoms 

class SymptomsStep(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["time_offset", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.Toffset = max(0.0, self.time_offset)
        self.Tend = max(0.0, self.end_time)

    def update_severity(self):
        time = self.timer.now
        if time > self.infection_start_time + self.Toffset and time < self.infection_start_time + self.Tend:
            severity = self.maxseverity
        else:
            severity = 0.

        self.last_time_updated = time
        self.severity = severity
