# celery-retry
Adds customizable, automated retry behavior to Celery tasks

## Usage
See below examples for usage notes on the various configurations available.

### Basic Usage
At minimum, simply add `autoretry=True` to the task decorator or in a call to `apply_async`.

```python
@celery.task(queue='demo', autoretry=True)
def demo_task():
  raise Exception('Always fails')
```

If not otherwise specified, utilizes default values for [`max_retries`](http://docs.celeryproject.org/en/3.1/reference/celery.app.task.html?#celery.app.task.Task.max_retries) and [`default_retry_delay`](http://docs.celeryproject.org/en/3.1/reference/celery.app.task.html?#celery.app.task.Task.default_retry_delay).  These values can also be applied explicitly
as defined in the Celery documentation.

### Linear
The following example will retry in 10, 20, and 30 seconds, respectively.

```python
@celery.task(queue='demo', autoretry=True, max_retries=3, linear_retry_delay=10)
def demo_task():
  raise Exception('Always fails')
```

### Exponential
Provide the base of the exponential delay calculation.  The following example will retry in 2, 4, and 8 seconds, respectively.

```python
@celery.task(queue='demo', autoretry=True, max_retries=3, exponential_retry_delay_base=2)
def demo_task():
  raise Exception('Always fails')
```

### Custom delay schedule
A user-defined delay schedule can also be provided, which need not fit any delay pattern.

```python
@celery.task(queue='demo', autoretry=True, max_retries=10, custom_retry_delay_schedule=(5, 15, 30, 90))
def demo_task():
  raise Exception('Always fails')
```

If the provided `max_retries` value exceeds the length of the provided tuple, the last value will be used for all remaining retries.

### Exception-based configurations
The `only_retry_for` and `prevent_retry_for` configuration options can be used to handle which Exceptions should trigger (or not trigger) a task retry.

#### only_retry_for
This task will not be retried because the raised Exception does not match the types provided.

```python
@celery.task(queue='demo', autoretry=True, max_retries=3, only_retry_for=(sqlalchemy.exc.OperationalError, sqlalchemy.exc.InternalError))
def demo_task():
  raise Exception('Always fails')
```

#### prevent_retry_for
This task will not be retried because it raises an Exception that is explicitly excluded from automatic retry behaviors.

```python

class NotEnoughItemsError(Exception): pass

@celery.task(queue='demo', autoretry=True, max_retries=3, prevent_retry_for=(NotEnoughItemsError, ))
def demo_task(x):
  y = [1, 2, 3]
  z = x + y
  
  if len(z) < 5:
    raise NotEnoughItemsError('too few items')
```

This configuration option may be useful to avoid retrying in cases when doing so would have no effect, such as an error explicitly raised in code or if the error is unrecoverable.

## Compatibility

- Python 2 and 3 compatible
- Designed to be compatible with Celery versions 3.x and 4.x, however 4.x compatibility has not been tested
