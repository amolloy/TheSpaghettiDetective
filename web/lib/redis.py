from django.conf import settings
import redis
import bson

REDIS = redis.Redis.from_url(
    settings.REDIS_URL, charset="utf-8", decode_responses=True)

# for binary messages, decoding must be omitted
BREDIS = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)

# redis key prefix
TUNNEL_PREFIX = "octoprinttunnel"

# max wait time for response from plugin
TUNNEL_RSP_TIMEOUT_SECS = 60

# drop unconsumed response from redis after this seconds
TUNNEL_RSP_EXPIRE_SECS = 60

# sent/received stats expiration
TUNNEL_STATS_EXPIRE_SECS = 3600 * 24 * 30 * 6


def printer_key_prefix(printer_id):
    return 'printer:{}:'.format(printer_id)


def print_key_prefix(print_id):
    return 'print:{}:'.format(print_id)


def printer_status_set(printer_id, mapping, ex=None):
    cleaned_mapping = {k: v for k, v in mapping.items() if v is not None}
    prefix = printer_key_prefix(printer_id) + 'status'
    REDIS.hmset(prefix, cleaned_mapping)
    if ex:
        REDIS.expire(prefix, ex)


def printer_status_get(printer_id, key=None):
    prefix = printer_key_prefix(printer_id) + 'status'
    if key:
        return REDIS.hget(prefix, key)
    else:
        return REDIS.hgetall(prefix)


def printer_status_delete(printer_id):
    return REDIS.delete(printer_key_prefix(printer_id) + 'status')


def printer_pic_set(printer_id, mapping, ex=None):
    cleaned_mapping = {k: v for k, v in mapping.items() if v is not None}
    prefix = printer_key_prefix(printer_id) + 'pic'
    REDIS.hmset(prefix, cleaned_mapping)
    if ex:
        REDIS.expire(prefix, ex)


def printer_pic_get(printer_id, key=None):
    prefix = printer_key_prefix(printer_id) + 'pic'
    if key:
        return REDIS.hget(prefix, key)
    else:
        return REDIS.hgetall(prefix)


def printer_settings_set(printer_id, mapping, ex=None):
    cleaned_mapping = {k: v for k, v in mapping.items() if v is not None}
    prefix = printer_key_prefix(printer_id) + 'settings'
    REDIS.hmset(prefix, cleaned_mapping)
    if ex:
        REDIS.expire(prefix, ex)


def printer_settings_get(printer_id, key=None):
    prefix = printer_key_prefix(printer_id) + 'settings'
    if key:
        return REDIS.hget(prefix, key)
    else:
        return REDIS.hgetall(prefix)


def print_num_predictions_incr(print_id):
    key = f'{print_key_prefix(print_id)}:pred'
    with REDIS.pipeline() as pipe:
        pipe.incr(key)
        # Assuming it'll be processed in 30 days.
        pipe.expire(key, 60*60*24*30)
        pipe.execute()


def print_num_predictions_get(print_id):
    key = f'{print_key_prefix(print_id)}:pred'
    return int(REDIS.get(key) or 0)


def print_num_predictions_delete(print_id):
    key = f'{print_key_prefix(print_id)}:pred'
    return REDIS.delete(key)


def print_high_prediction_add(print_id, prediction, timestamp, maxsize=180):

    key = f'{print_key_prefix(print_id)}:hp'
    with REDIS.pipeline() as pipe:
        pipe.zadd(key, {timestamp: prediction})
        pipe.zremrangebyrank(key, 0, (-1*maxsize+1))
        # Assuming it'll be processed in 3 days.
        pipe.expire(key, 60*60*24*3)
        pipe.execute()


def print_highest_predictions_get(print_id):
    key = f'{print_key_prefix(print_id)}:hp'
    return REDIS.zrevrange(key, 0, -1, withscores=True)


def print_progress_set(print_id, progress_percent):
    key = f'{print_key_prefix(print_id)}:pct'
    REDIS.set(key, str(progress_percent), ex=60*60*24*2)


def print_progress_get(print_id):
    key = f'{print_key_prefix(print_id)}:pct'
    return int(REDIS.get(key) or 0)


def octoprinttunnel_stats_key(date):
    dt = date.strftime('%Y%m')
    return f'{TUNNEL_PREFIX}.stats.{dt}'


def octoprinttunnel_update_sent_stats(date, user_id, printer_id, transport, delta):
    key = octoprinttunnel_stats_key(date)
    with BREDIS.pipeline() as pipe:
        pipe.hincrby(key, f'{user_id}.{printer_id}.sent.{transport}', delta)
        pipe.hincrby(key, f'{user_id}.{printer_id}.sent', delta)
        pipe.hincrby(key, f'{user_id}.{printer_id}.total', delta)
        pipe.hincrby(key, f'{user_id}.sent.{transport}', delta)
        pipe.hincrby(key, f'{user_id}.sent', delta)
        pipe.hincrby(key, f'{user_id}.total', delta)
        pipe.hincrby(key, f'sent.{transport}', delta)
        pipe.hincrby(key, 'sent', delta)
        pipe.hincrby(key, f'total.{transport}', delta)
        pipe.hincrby(key, 'total', delta)
        pipe.expire(key, TUNNEL_STATS_EXPIRE_SECS)
        pipe.execute()


def octoprinttunnel_update_received_stats(date, user_id, printer_id, transport, delta):
    key = octoprinttunnel_stats_key(date)
    with BREDIS.pipeline() as pipe:
        pipe.hincrby(key, f'{user_id}.{printer_id}.received.{transport}', delta)
        pipe.hincrby(key, f'{user_id}.{printer_id}.received', delta)
        pipe.hincrby(key, f'{user_id}.{printer_id}.total', delta)
        pipe.hincrby(key, f'{user_id}.received.{transport}', delta)
        pipe.hincrby(key, f'{user_id}.received', delta)
        pipe.hincrby(key, f'{user_id}.total', delta)
        pipe.hincrby(key, f'received.{transport}', delta)
        pipe.hincrby(key, 'received', delta)
        pipe.hincrby(key, f'total.{transport}', delta)
        pipe.hincrby(key, 'total', delta)
        pipe.expire(key, TUNNEL_STATS_EXPIRE_SECS)
        pipe.execute()


def octoprinttunnel_get_stats(date):
    key = octoprinttunnel_stats_key(date)
    return BREDIS.hgetall(key)


def octoprinttunnel_http_response_set(ref, data,
                                      expire_secs=TUNNEL_RSP_EXPIRE_SECS):
    key = f"{TUNNEL_PREFIX}.{ref}"
    with BREDIS.pipeline() as pipe:
        pipe.lpush(key, bson.dumps(data))
        pipe.expire(key, expire_secs)
        pipe.execute()


def octoprinttunnel_http_response_get(ref, timeout_secs=TUNNEL_RSP_TIMEOUT_SECS):
    # no way to delete key in after blpop in a pipeline as
    # blpop does not block in that case..
    key = f"{TUNNEL_PREFIX}.{ref}"
    ret = BREDIS.blpop(key, timeout=timeout_secs)
    if ret is not None and ret[1] is not None:
        BREDIS.delete(key)
        return bson.loads(ret[1])
    return None
