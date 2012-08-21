""" supybot-fedmsg - augment other supybot plugins to emit fedmsg messages.

:Author: Ralph Bean <rbean@redhat.com>
"""

import fedmsg
import socket
import supybot.callbacks
import threading
import time
import types


class Fedmsg(supybot.callbacks.Plugin):
    """ Use this plugin to fedmsg-enable various other supybot plugins.

    It modifies other plugins at startup and does nothing else.

    Supported plugins are:
        - supybot-meetbot

    """

    def __init__(self, irc):
        super(Fedmsg, self).__init__(irc)

        # Initialize fedmsg resources.
        fedmsg.init(name="supybot." + socket.gethostname())

        # Launch in a thread to duckpunch *after* the other plugins
        # have been setup.
        thread = Injector()
        thread.start()


class Injector(threading.Thread):
    """ Injector our code into other supybot plugins.

    Wait 2 seconds before doing so to help make sure they've loaded
    before we try.
    """

    def run(self):
        # Sleep 2 seconds
        time.sleep(2)

        # Then, do our thing.
        self._duckpunch_meetbot()

        # TODO -- _duckpunch_announce()

    def _duckpunch_meetbot(shmelf):
        """ Replace some of meetbot's methods with our own which simply call
        meetbot's original method, and then emit a fedmsg message before
        returning.
        """

        try:
            import sys
            target_cls = sys.modules['MeetBot.meeting'].Meeting
        except KeyError:
            raise ValueError(
                "MeetBot not yet enabled.  Try Fedmsg again later."
            )

        tap_points = {
            'do_startmeeting': 'startmeeting',
            'do_endmeeting': 'endmeeting',
        }
        for target_method, topic in tap_points.items():

            def wrapper_factory(topic):
                old_method = getattr(target_cls, target_method).__func__

                def wrapper(self, *args, **kw):
                    # Call the target plugin's original code first and save the
                    # result.
                    result = old_method(self, *args, **kw)

                    # Emit on "org.fedoraproject.prod.meetbot.startmeeting"
                    fedmsg.publish(
                        modname="meetbot",
                        topic=topic,
                        msg=dict(
                            owner=self.owner,
                            chairs=self.chairs,
                            attendees=self.attendees,
                            url=self.config.filename(url=True),
                            meeting_topic=self._meetingTopic,
                            channel=self.channel,
                        ),
                    )

                    # Return the original result from the target plugin.
                    return result

                return wrapper

            # Build the new method and attach it to the target class.
            new_method = wrapper_factory(topic=topic)
            setattr(target_cls, target_method, new_method)

    def _duckpunch_announce(shmelf):
        """ Instrument the announce plugin to emit messages. """
        raise NotImplementedError


Class = Fedmsg
