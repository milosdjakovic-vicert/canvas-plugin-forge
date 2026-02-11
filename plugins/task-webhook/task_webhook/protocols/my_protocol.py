from canvas_sdk.events import EventType
from canvas_sdk.protocols import BaseProtocol
from canvas_sdk.utils import Http
from logger import log


class Protocol(BaseProtocol):
    """
    When a task is created or updated, hit a webhook
    """

    RESPONDS_TO = [
        EventType.Name(EventType.TASK_CREATED),
        EventType.Name(EventType.TASK_UPDATED),
    ]

    def compute(self):
        """
        Notify our server of tasks as they are created.
        """
        url = f"https://webhook.site/{self.secrets['WEBHOOK_ID']}"
        headers = {"Authorization": f"Bearer {self.secrets['AUTH_TOKEN']}"}

        # self.event.type is a member of the EventType enum corresponding to
        # one of the event types in the plugin's RESPONDS_TO attribute
        verb = 'created' if self.event.type == EventType.TASK_CREATED else 'updated'

        payload = {
            "message": f"A Task was {verb}!",
            "resource_id": self.target,
        }

        http = Http()
        response = http.post(url, json=payload, headers=headers)

        # You can also get the name of the event as as string using EventType.Name()
        event_name = EventType.Name(self.event.type)

        if response.ok:
            log.info(f"Successfully notified API of {event_name}")
        else:
            log.info(f"Notification of {event_name} unsuccessful. =[")

        return []
