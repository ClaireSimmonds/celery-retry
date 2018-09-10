from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import inspect
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from celery import Task

import celery_retry


test_exception = Exception('Something went wrong')


class TestException(Exception): pass


class SimpleTask(object): pass


class SuccessfulTask(celery_retry.autoretry_task_factory(Task)):
    def run(self):
        return True


class ExceptionTask(celery_retry.autoretry_task_factory(Task)):
    def run(self):
        raise test_exception


class CeleryRetryTestCase(unittest.TestCase):
    pass


class AutoRetryTaskFactoryTestCase(CeleryRetryTestCase):
    def test_return_value_is_class(self):
        test_cls = celery_retry.autoretry_task_factory(Task)
        self.assertTrue(inspect.isclass(test_cls))

    def test_return_value_type_is_type(self):
        test_cls = celery_retry.autoretry_task_factory(SimpleTask)
        self.assertIs(type(test_cls), type)

    def test_return_value_is_subclass_of_given_task_class(self):
        given_task_class = Task
        test_cls = celery_retry.autoretry_task_factory(given_task_class)
        self.assertTrue(issubclass(test_cls, given_task_class))

    def test_return_value_class_method_resolution_order(self):
        given_task_class = Task
        test_cls = celery_retry.autoretry_task_factory(given_task_class)
        self.assertListEqual(test_cls.mro(), [test_cls, celery_retry.AutoRetryTaskMixin, given_task_class, object])


class AutoRetryTaskMixinTestCase(CeleryRetryTestCase):
    def setUp(self):
        super(AutoRetryTaskMixinTestCase, self).setUp()
        self.test_class = celery_retry.autoretry_task_factory(Task)


class AutoRetryTaskMixinCallTestCase(AutoRetryTaskMixinTestCase):
    def test_autoretry_disabled_calls_task_immediately(self):
        inst = SuccessfulTask()
        self.assertTrue(inst.__call__())

    def test_autoretry_enabled_calls_task_after_checking_for_exceptions(self):
        inst = SuccessfulTask()
        inst.autoretry = True

        with mock.patch.object(
            inst,
            '_get_categorized_exceptions',
            return_value=((), ())
        ) as mock_get_categorized_exceptions:
            value = inst.__call__()

        self.assertTrue(value)
        mock_get_categorized_exceptions.assert_called_once_with()

    def test_reraise_if_prevent_retry_for_enabled_for_originally_raised_exception(self):
        inst = ExceptionTask()
        inst.autoretry = True
        inst.prevent_retry_for = (Exception, )

        with self.assertRaises(Exception):
            inst.__call__()

    def test_uses_constant_delay_if_option_enabled(self):
        inst = ExceptionTask()
        inst.autoretry = True
        inst.constant_retry_delay = 2

        with mock.patch.object(inst, 'retry') as mock_retry:
            inst.__call__()

        mock_retry.assert_called_once_with(**dict(exc=test_exception, countdown=2))

    def test_gets_linear_delay_if_option_enabled(self):
        inst = ExceptionTask()
        inst.autoretry = True
        inst.linear_retry_delay = 2

        with mock.patch.object(inst, 'get_linear_delay', return_value=2) as mock_get_linear_delay:
            with mock.patch.object(inst, 'retry') as mock_retry:
                inst.__call__()

        mock_get_linear_delay.assert_called_once_with(2, 0)
        mock_retry.assert_called_once_with(**dict(exc=test_exception, countdown=2))

    def test_gets_exponential_delay_if_option_enabled(self):
        inst = ExceptionTask()
        inst.autoretry = True
        inst.exponential_retry_delay_base = 2

        with mock.patch.object(inst, 'get_exponential_delay', return_value=2) as mock_get_exponential_delay:
            with mock.patch.object(inst, 'retry') as mock_retry:
                inst.__call__()

        mock_get_exponential_delay.assert_called_once_with(2, 0)
        mock_retry.assert_called_once_with(**dict(exc=test_exception, countdown=2))

    def test_gets_custom_delay_if_option_enabled(self):
        inst = ExceptionTask()
        inst.autoretry = True
        inst.custom_retry_delay_schedule = (2, 3, 4)

        with mock.patch.object(inst, 'get_custom_delay', return_value=2) as mock_get_custom_delay:
            with mock.patch.object(inst, 'retry') as mock_retry:
                inst.__call__()

        mock_get_custom_delay.assert_called_once_with((2, 3, 4), 0)
        mock_retry.assert_called_once_with(**dict(exc=test_exception, countdown=2))


class AutoRetryTaskMixinGetCategorizedExceptionsTestCase(AutoRetryTaskMixinTestCase):
    def test_retry_for_all_exceptions_if_overrides_None(self):
        instance = self.test_class()
        self.assertIsNone(instance.only_retry_for)
        self.assertIsNone(instance.prevent_retry_for)

        retry_exc, raise_exc = instance._get_categorized_exceptions()
        self.assertTupleEqual(retry_exc, (Exception, ))
        self.assertTupleEqual(raise_exc, ())

    def test_only_retry_for_value_overrides_default(self):
        instance = self.test_class()
        instance.only_retry_for = (TestException, )

        retry_exc, raise_exc = instance._get_categorized_exceptions()
        self.assertTupleEqual(retry_exc, (TestException, ))
        self.assertTupleEqual(raise_exc, ())

    def test_prevent_retry_for_override_populates_value(self):
        instance = self.test_class()
        instance.prevent_retry_for = (TestException, )

        retry_exc, raise_exc = instance._get_categorized_exceptions()
        self.assertTupleEqual(retry_exc, (Exception, ))
        self.assertTupleEqual(raise_exc, (TestException, ))


class AutoRetryTaskMixinGetLinearDelayTestCase(AutoRetryTaskMixinTestCase):
    def test_return_value(self):
        self.assertEqual(celery_retry.AutoRetryTaskMixin.get_linear_delay(5, 0), 5)


class AutoRetryTaskMixinGetExponentialDelay(AutoRetryTaskMixinTestCase):
    def test_return_value(self):
        self.assertEqual(celery_retry.AutoRetryTaskMixin.get_exponential_delay(2, 0), 2)


class AutoRetryTaskMixinGetCustomDelayTestCase(AutoRetryTaskMixinTestCase):
    def setUp(self):
        super(AutoRetryTaskMixinGetCustomDelayTestCase, self).setUp()
        self.delay_schedule = (2, 5, 10, 15)

    def test_returns_value_at_index_matching_retry_attempt_count(self):
        self.assertEqual(celery_retry.AutoRetryTaskMixin.get_custom_delay(self.delay_schedule, 2), 10)

    def test_returns_last_value_if_retry_count_exceeds_tuple_length(self):
        self.assertEqual(celery_retry.AutoRetryTaskMixin.get_custom_delay(self.delay_schedule, 7), 15)
