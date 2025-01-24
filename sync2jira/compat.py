def extract_message_body(msg):
    """Strip off the message envelope.

    Handle both fedmsg and fedora-messaging style message bodies.
    """

    if "body" in msg:
        return msg["body"]
    elif "msg" in msg:
        return msg["msg"]
    else:
        raise KeyError(
            f"Unrecognized message format with keys {msg.keys()}. Expected either 'msg' or 'body'"
        )
