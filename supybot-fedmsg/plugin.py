""" supybot-fedmsg - augment other supybot plugins to emit fedmsg messages.

:Author: Ralph Bean <rbean@redhat.com>
"""

import types
import supybot.callbacks


class Fedmsg(supybot.callbacks.Plugin):
    """ Use this plugin to fedmsg-enable various other supybot plugins.

    It modifies other plugins at startup and does nothing else.

    Supported plugins are:
        - supybot-meetbot

    """

    def __init__(self, irc):
        super(FedmsgPlugin, self).__init__(irc)
        # TODO -- Check config file for the green light.
        self._duckpunch_meetbot()
        # TODO -- _duckpunch_announce()

    def _duckpunch_meetbot(self):
        """ Replace some of meetbot's methods with our own which simply call
        meetbot's original method, and then emit a fedmsg message before
        returning.
        """

        from supybot.plugins.MeetBot.plugin import Class as target_class

        tap_points = {
            'do_startmeeting': 'startmeeting',
            'do_endmeeting': 'endmeeting',
        }
        for target_method, topic in tap_points.items():

            def wrapper_factory():
                old_method = getattr(target_class, target_method).__func__

                def wrapper(self, *args, **kw):
                    result = old_method(self, *args, **kw)
                    # Emit on "org.fedoraproject.prod.meetbot.startmeeting"
                    fedmsg.publish(topic=topic, msg=dict(args=args, kw=kw))
                    return result

                return wrapper

            # Build the new method and attach it to the target class.
            new_method = types.MethodType(wrapper_factory(), target_class)
            setattr(target_class, target_method, new_method)

    def _duckpunch_announce(self):
        """ Instrument the announce code to emit messages. """
        raise NotImplementedError


Class = FedmsgPlugin
