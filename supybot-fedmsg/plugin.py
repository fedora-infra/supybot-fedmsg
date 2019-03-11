""" supybot-fedmsg - augment other supybot plugins to emit fedora-messaging messages.

:Author: Ralph Bean <rbean@redhat.com>
"""

import socket
import supybot.callbacks
import threading
import time

from fedora_messaging.api import publish, Message
from fedora_messaging.exceptions import PublishReturned, ConnectionException

# A flag placed on wrapped methods to note we have already wrapped them once.
SENTINEL = '_sentinel_flag'

# When we start up, we try to wrap meetbot.  But if it's not there, we die and
# create a new thread that wakes up in 60s and tries again.
INTERVAL = 60


def already_wrapped(method):
    """ Return true if it looks like we have already wrapped a target. """
    return hasattr(method, SENTINEL) or hasattr(method.__func__, SENTINEL)


class Fedmsg(supybot.callbacks.Plugin):
    """ Use this plugin to fedmsg-enable various other supybot plugins.

    It modifies other plugins at startup and does nothing else.

    Supported plugins are:
        - supybot-meetbot

    """

    def __init__(self, irc):
        super(Fedmsg, self).__init__(irc)

        # Launch in a thread to duckpunch *after* the other plugins
        # have been set up.
        thread = Injector()
        thread.start()


class Injector(threading.Thread):
    """ Injector our code into other supybot plugins.

    Wait 2 seconds before doing so to help make sure they've loaded
    before we try.
    """

    def run(shmelf):
        """ Replace some of meetbot's methods with our own which simply call
        meetbot's original method, and then emit a fedmsg message before
        returning.
        """

        time.sleep(INTERVAL)

        try:
            import sys
            target_cls = sys.modules['MeetBot.meeting'].Meeting
        except KeyError:
            # Start another thread to finish our work later.
            another_thread = Injector()
            another_thread.start()
            print "MeetBot not yet enabled."
            print "  Will try to wrap fedmsg again in %is" % INTERVAL
            return  # Bail out early.

        tap_points = {
            'do_startmeeting': 'meeting.start',
            'do_endmeeting': 'meeting.complete',
            'do_topic': 'meeting.topic.update',

            'do_agreed':    'meeting.item.agreed',
            'do_accepted':  'meeting.item.accepted',
            'do_rejected':  'meeting.item.rejected',

            'do_action':    'meeting.item.action',
            'do_info':      'meeting.item.info',
            'do_idea':      'meeting.item.idea',
            'do_help':      'meeting.item.help',  # We map #help and #halp
            'do_halp':      'meeting.item.help',  # to the same topic...
            'do_link':      'meeting.item.link',
        }
        for target_method, topic in tap_points.items():

            def wrapper_factory(topic):
                old_method = getattr(target_cls, target_method)

                def wrapper(self, *args, **kw):
                    # Call the target plugin's original code first and save the
                    # result.
                    result = old_method.__func__(self, *args, **kw)

                    # Include the owner of the meeting in the chairs dict just
                    # in case they never explicitly #chair'd themselves.
                    chairs = self.chairs
                    chairs[self.owner] = chairs.get(self.owner, True)

                    payload = dict(
                        owner=self.owner,
                        chairs=chairs,
                        attendees=self.attendees,
                        url=self.config.filename(url=True),
                        meeting_topic=self._meetingTopic,
                        topic=self.currenttopic,
                        channel=self.channel,
                        details=kw,  # This includes the 'who' and 'what'
                    )
                    try:
                        msg = Message(
                            topic="meetbot.{}.v1".format(topic),
                            body=payload,
                        )
                        publish(msg)
                    except PublishReturned as e:
                        print "Fedora Messaging broker rejected message {}: {}".format(msg.id, e)
                    except ConnectionException as e:
                        print "Error sending message {}: {}".format(msg.id, e)

                    # Return the original result from the target plugin.
                    return result

                # Set a flag indicating that we are wrapping the other plugin
                setattr(wrapper, SENTINEL, True)

                if already_wrapped(old_method):
                    return old_method
                else:
                    return wrapper

            # Build the new method and attach it to the target class.
            new_method = wrapper_factory(topic=topic)
            setattr(target_cls, target_method, new_method)


Class = Fedmsg
