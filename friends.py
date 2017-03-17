# friends related

from model import db, Connection, User

def friends_or_pending(user_a_id, user_b_id):
    """
    check user_a and user_b are friends or pending
    REMEMBER to check both directions!
    """

    friends = db.session.query(Connection).filter(Connection.user_a_id == user_a_id,
                                                     Connection.user_b_id == user_b_id,
                                                     Connection.status == "Friends").first()
    if not friends:
        friends = db.session.query(Connection).filter(Connection.user_a_id == user_b_id,
                                                        Connection.user_b_id == user_a_id,
                                                        Connection.status == "Friends").first()

    pending = db.session.query(Connection).filter(Connection.user_a_id == user_a_id,
                                                     Connection.user_b_id == user_b_id,
                                                     Connection.status == "Pending").first()

    if not pending:
        pending = db.session.query(Connection).filter(Connection.user_a_id == user_b_id,
                                                        Connection.user_b_id == user_a_id,
                                                        Connection.status == "Pending").first()        

    return friends, pending


def get_friend_requests(user_id):
    """
    get pending sent and received friend requests
    """

    received_friend_requests = db.session.query(User).join(Connection, Connection.user_a_id == User.user_id).\
                                                        filter(Connection.user_b_id == user_id,
                                                                Connection.status == "Pending").all()

    sent_friend_requests = db.session.query(User).join(Connection, Connection.user_b_id == User.user_id).\
                                                    filter(Connection.user_a_id == user_id,
                                                            Connection.status == "Pending").all()

    return received_friend_requests, sent_friend_requests


def get_friends(user_id):
    """
    return user's friends
    REMEMBER to check both directions!
    """

    friends_received = db.session.query(User).join(Connection, Connection.user_b_id == User.user_id).\
                                                filter(Connection.user_a_id == user_id,
                                                        Connection.status == "Friends")


    friends_sent = db.session.query(User).join(Connection, Connection.user_a_id == User.user_id).\
                                            filter(Connection.user_b_id == user_id,
                                                    Connection.status == "Friends")

    friends = friends_received.union(friends_sent)

    return friends
