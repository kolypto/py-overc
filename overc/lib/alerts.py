import os
import shlex
import subprocess
import logging

logger = logging.getLogger(__name__)


class AlertPlugin(object):
    """ Alert plugin """

    def __init__(self, name, cwd, command):
        self.name = name
        self.cwd = cwd
        self.command_str = command
        self.command = shlex.split(self.command_str)

    def send(self, message):
        """ Send a message
        :param message: Message
        :type message: unicode
        :exception OSError: plugin not found
        :exception subprocess.CalledProcessError: plugin execution error (non-zero return code)
        """
        # Execute
        process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        try:
            # Run
            process.stdin.write(message)
            process.stdin.close()

            # Wait, analyze retcode
            process.wait()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, self.command_str, '')
        finally:
            process.stdout.close()


def send_alert_with_plugins(alert_plugins, message):
    """ Fetch notifications config and send messages
    :param alert_plugins: List of alert plugins to use
    :type alert_plugins: list[AlertPlugin]
    :param message: Alert message to send
    :type message: unicode
    """
    # TODO: execute alert scripts in parallel!

    # Send
    plugin_failures = []
    for plugin in alert_plugins:
        try:
            plugin.send(message)
        except Exception as e:
            logger.exception('Alert plugin `{}` command failed: {}'.format(plugin.name, plugin.command_str))
            plugin_failures.append(
                'Alert plugin `{}` failed: {}'.format(plugin.name, e)
            )

    # No failures? Good!
    if not plugin_failures:
        return

    # Report plugin errors with all available plugins
    plugin_failure_message = "\n".join(plugin_failures)
    n_sent = 0
    for plugin in alert_plugins:
        try:
            plugin.send(plugin_failure_message)
            n_sent += 1
        except Exception:
            logger.exception('Failed to send fatal plugin notification!')

    # Fatal error
    if n_sent == 0:
        logger.fatal('NONE of the plugins could send the message:\n' + plugin_failure_message)
