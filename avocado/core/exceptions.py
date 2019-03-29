# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Exception classes, useful for tests, and other parts of the framework code.
"""
from functools import wraps
import types


def fail_on(exceptions=None):
    """
    Fail the test when decorated function produces exception of the specified
    type.

    (For example, our method may raise IndexError on tested software failure.
    We can either try/catch it or use this decorator instead)

    :param exceptions: Tuple or single exception to be assumed as
                       test fail [Exception]
    :note: self.error and self.skip behavior remains intact
    :note: To allow simple usage param "exceptions" must not be callable
    """
    func = False
    if exceptions is None:
        exceptions = Exception
    elif isinstance(exceptions, types.FunctionType):     # @fail_on without ()
        func = exceptions
        exceptions = Exception

    def decorate(func):
        """ Decorator """
        @wraps(func)
        def wrap(*args, **kwargs):
            """ Function wrapper """
            try:
                return func(*args, **kwargs)
            except TestBaseException:
                raise
            except exceptions as details:
                raise TestFail(str(details))
        return wrap
    if func:
        return decorate(func)
    return decorate


class JobBaseException(Exception):

    """
    The parent of all job exceptions.

    You should be never raising this, but just in case, we'll set its
    status' as FAIL.
    """
    status = "FAIL"


class JobError(JobBaseException):

    """
    A generic error happened during a job execution.
    """
    status = "ERROR"


class OptionValidationError(Exception):

    """
    An invalid option was passed to the test runner
    """
    status = "ERROR"


class TestBaseException(Exception):

    """
    The parent of all test exceptions.

    You should be never raising this, but just in case, we'll set its
    status' as FAIL.
    """
    status = "FAIL"


class TestSetupFail(TestBaseException):

    """
    Indicates an error during a setup or cleanup procedure.
    """
    status = "ERROR"


class TestError(TestBaseException):

    """
    Indicates that the test was not fully executed and an error happened.

    This is the sort of exception you raise if the test was partially
    executed and could not complete due to a setup, configuration,
    or another fatal condition.
    """
    status = "ERROR"


class NotATestError(TestBaseException):

    """
    Indicates that the file is not a test.

    Causes: Non executable, non python file or python module without
    an avocado test class in it.
    """
    status = "NOT_A_TEST"


class TestNotFoundError(TestBaseException):

    """
    Indicates that the test was not found in the test directory.
    """
    status = "ERROR"


class TestTimeoutInterrupted(TestBaseException):

    """
    Indicates that the test did not finish before the timeout specified.
    """
    status = "INTERRUPTED"


class TestTimeoutSkip(TestBaseException):

    """
    Indicates that the test is skipped due to a job timeout.
    """
    status = "SKIP"


class TestInterruptedError(TestBaseException):

    """
    Indicates that the test was interrupted by the user (Ctrl+C)
    """
    status = "INTERRUPTED"


class TestAbortError(TestBaseException):

    """
    Indicates that the test was prematurely aborted.
    """
    status = "ERROR"


class TestSkipError(TestBaseException):

    """
    Indictates that the test is skipped.

    Should be thrown when various conditions are such that the test is
    inappropriate. For example, inappropriate architecture, wrong OS version,
    program being tested does not have the expected capability (older version).
    """
    status = "SKIP"


class TestFail(TestBaseException, AssertionError):

    """
    Indicates that the test failed.

    TestFail inherits from AssertionError in order to keep compatibility
    with vanilla python unittests (they only consider failures the ones
    deriving from AssertionError).
    """
    status = "FAIL"


class HealthCheckFail(TestBaseException, AssertionError):

    """
    Indicates that the test health check failed.

    HealthCheckFail inherits from AssertionError in order to keep compatibility
    with vanilla python unittests (they only consider failures the ones
    deriving from AssertionError).
    """
    status = "FAIL"


class TestWarn(TestBaseException, AssertionError):

    """
    Indicates that the test failed.

    TestFail inherits from AssertionError in order to keep compatibility
    with vanilla python unittests (they only consider failures the ones
    deriving from AssertionError).
    """
    status = "WARN"


class InjectionFail(TestBaseException):
    """
    Indicate the reliability injection failure
    """
    status = "FAIL"


class APIException(TestBaseException):
    """Base API Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    status = "ERROR"


class RestClientException(APIException):
    pass


class OtherRestClientException(RestClientException):
    pass


class ServerRestClientException(RestClientException):
    pass


class ClientRestClientException(RestClientException):
    pass


class InvalidHttpSuccessCode(OtherRestClientException):
    message = "The success code is different than the expected one"


class BadRequest(ClientRestClientException):
    status_code = 400
    status = "ERROR"
    message = "Bad request"


class Unauthorized(ClientRestClientException):
    status_code = 401
    status = "ERROR"
    message = 'Unauthorized'


class Forbidden(ClientRestClientException):
    status_code = 403
    status = "ERROR"
    message = "Forbidden"


class NotFound(ClientRestClientException):
    status_code = 404
    message = "Object not found"


class Conflict(ClientRestClientException):
    status_code = 409
    message = "An object with that identifier already exists"


class Gone(ClientRestClientException):
    status_code = 410
    message = "The requested resource is no longer available"


class RateLimitExceeded(ClientRestClientException):
    status_code = 413
    message = "Rate limit exceeded"


class OverLimit(ClientRestClientException):
    status_code = 413
    message = "Request entity is too large"


class InvalidContentType(ClientRestClientException):
    status_code = 415
    message = "Invalid content type provided"


class UnprocessableEntity(ClientRestClientException):
    status_code = 422
    message = "Unprocessable entity"


class ServerFault(ServerRestClientException):
    status_code = 500
    status = "ERROR"
    message = "Got server fault"


class NotImplemented(ServerRestClientException):
    status_code = 501
    message = "Got NotImplemented error"


class TimeoutException(OtherRestClientException):
    status = "FAIL"
    message = "Request timed out"


class ResponseWithNonEmptyBody(OtherRestClientException):
    message = ("RFC Violation! Response with %(status)d HTTP Status Code "
               "MUST NOT have a body")


class ResponseWithEntity(OtherRestClientException):
    status = "FAIL"
    message = ("RFC Violation! Response with 205 HTTP Status Code "
               "MUST NOT have an entity")


class InvalidHTTPResponseBody(OtherRestClientException):
    status = "FAIL"
    message = "HTTP response body is invalid json or xml"


class InvalidHTTPResponseHeader(OtherRestClientException):
    status = "FAIL"
    message = "HTTP response header is invalid"


class UnexpectedContentType(OtherRestClientException):
    status = "FAIL"
    message = "Unexpected content type provided"


class UnexpectedResponseCode(OtherRestClientException):
    status = "FAIL"
    message = "Unexpected response code received"


class InvalidConfiguration(APIException):
    message = "Invalid Configuration"


class InvalidIdentityVersion(APIException):
    message = "Invalid version %(identity_version)s of the identity service"


class InvalidStructure(APIException):
    message = "Invalid structure of table with details"


class InvalidAPIVersionString(APIException):
    message = ("API Version String %(version)s is of invalid format. Must "
               "be of format MajorNum.MinorNum or string 'latest'.")


class JSONSchemaNotFound(APIException):
    message = ("JSON Schema for %(version)s is not found in\n"
               " %(schema_versions_info)s")


class InvalidAPIVersionRange(APIException):
    message = ("The API version range is invalid.")


class BadAltAuth(APIException):
    """Used when trying and failing to change to alt creds.

    If alt creds end up the same as primary creds, use this
    exception. This is often going to be the case when you assume
    project_id is in the url, but it's not.

    """
    message = "The alt auth looks the same as primary auth for %(part)s"


class ServiceClientRegistrationException(APIException):
    message = ("Error registering module %(name)s in path %(module_path)s, "
               "with service %(service_version)s and clients "
               "%(client_names)s: %(detailed_error)s")


class VMNotFound(TestBaseException):

    """
    Indicates an error that VM could not be found
    """
    status = "ERROR"


class ResourceTypeNotFound(TestBaseException):

    """
    Indicates an error that the key of resource could not be found
    """
    status = "ERROR"


class ServerGroupNotFound(TestBaseException):

    """
    Indicates an error that server group could not be found
    """
    status = "ERROR"


class VolumeBuildErrorException(TestBaseException):
    message = "Volume %(volume_id)s failed to build and is in ERROR status"


class VolumeRestoreErrorException(TestBaseException):
    message = "Volume %(volume_id)s failed to restore and is in ERROR status"
