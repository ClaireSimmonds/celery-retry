# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals


class AutoRetryTaskMixin(object):
    abstract = True
    autoretry = False
    constant_retry_delay = None
    linear_retry_delay = None
    exponential_retry_delay_base = None
    custom_retry_delay_schedule = None
    only_retry_for = None
    prevent_retry_for = None

    def __call__(self, *args, **kwargs):
        if self.autoretry is True:
            retry_exceptions, raise_exceptions = self._get_categorized_exceptions()

            try:
                return super(AutoRetryTaskMixin, self).__call__(*args, **kwargs)
            except raise_exceptions as e:
                raise e
            except retry_exceptions as e:
                delay = self.default_retry_delay
                if self.constant_retry_delay is not None:
                    delay = self.constant_retry_delay
                if self.linear_retry_delay is not None:
                    delay = self.get_linear_delay(self.linear_retry_delay, self.request.retries)
                elif self.exponential_retry_delay_base is not None:
                    delay = self.get_exponential_delay(self.exponential_retry_delay_base, self.request.retries)
                elif self.custom_retry_delay_schedule is not None:
                    delay = self.get_custom_delay(self.custom_retry_delay_schedule, self.request.retries)

                self.retry(exc=e, countdown=delay)
        else:
            return super(AutoRetryTaskMixin, self).__call__(*args, **kwargs)

    def _get_categorized_exceptions(self):
        retry_exceptions = (Exception, )
        raise_exceptions = tuple()

        if self.only_retry_for is not None:
            retry_exceptions = self.only_retry_for
        elif self.prevent_retry_for is not None:
            raise_exceptions = self.prevent_retry_for

        return retry_exceptions, raise_exceptions

    @staticmethod
    def get_linear_delay(delay_value, retry_count):
        return delay_value * (retry_count + 1)

    @staticmethod
    def get_exponential_delay(delay_base, retry_count):
        return delay_base ** (retry_count + 1)

    @staticmethod
    def get_custom_delay(delay_schedule, retry_count):
        try:
            return delay_schedule[retry_count]
        except IndexError:
            return delay_schedule[-1]


def autoretry_task_factory(task_cls):
    return type(str('AutoRetryTask'), (AutoRetryTaskMixin, task_cls), {})
