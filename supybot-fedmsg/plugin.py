""" supybot-fedmsg - augment other supybot plugins to emit fedmsg messages.

:Author: Ralph Bean <rbean@redhat.com>
"""

import fedmsg
import socket
import supybot.callbacks
import threading
import time

# A flag placed on wrapped methods to note we have already wrapped them once.
SENTINEL = '_sentinel_flag'


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

        # If fedmsg was already initialized, let's not re-do that.
        if getattr(getattr(fedmsg, '__local', None), '__context', None):
            print "Not reinitializing fedmsg."
        else:
            # Initialize fedmsg resources.
            hostname = socket.gethostname().split('.', 1)[0]
            fedmsg.init(name="supybot." + hostname)

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

                    # Emit on "org.fedoraproject.prod.meetbot.meeting.start"
                    fedmsg.publish(
                        modname="meetbot",
                        topic=topic,
                        msg=dict(
                            owner=self.owner,
                            chairs=chairs,
                            attendees=self.attendees,
                            url=self.config.filename(url=True),
                            meeting_topic=self._meetingTopic,
                            topic=self.currenttopic,
                            channel=self.channel,
                            details=kw,  # This includes the 'who' and 'what'
                        ),
                    )

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

    def _duckpunch_announce(shmelf):
        """ Instrument the announce plugin to emit messages. """
        raise NotImplementedError


Class = Fedmsg
