#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
Custom validators for spikeChecker UI components.
"""
import re

from Qt import QtGui


class AlphanumericValidator(QtGui.QValidator):
    """Validator that allows only alphanumeric characters and underscores.

    This validator is useful for fields that require identifiers,
    such as prefix names, suffix names, etc.
    """

    def validate(self, input_text: str, pos: int) -> QtGui.QValidator.State:
        """Validate input text.

        Args:
            input_text (str): Text to validate.
            pos (int): Cursor position.

        Returns:
            QtGui.QValidator.State: Validation result.
                - Acceptable: Text is valid
                - Invalid: Text contains invalid characters
        """
        if not input_text:
            return QtGui.QValidator.Acceptable

        # Only allow alphanumeric and underscore
        pattern = r"^[a-zA-Z0-9_]+$"
        if re.match(pattern, input_text):
            return QtGui.QValidator.Acceptable

        return QtGui.QValidator.Invalid

    def fixup(self, input_text: str) -> str:
        """Fix invalid input by removing invalid characters.

        Args:
            input_text (str): Input text to fix.

        Returns:
            str: Fixed text with only valid characters.
        """
        # Remove invalid characters using regex
        return re.sub(r"[^a-zA-Z0-9_]", "", input_text)


class ASCIIValidator(QtGui.QValidator):
    """Validator that allows only ASCII characters.

    This validator prevents Japanese and other non-ASCII characters
    from being entered, which is useful for Maya node names and identifiers.
    """

    def validate(self, input_text: str, pos: int) -> QtGui.QValidator.State:
        """Validate input text.

        Args:
            input_text (str): Text to validate.
            pos (int): Cursor position.

        Returns:
            QtGui.QValidator.State: Validation result.
                - Acceptable: Text is valid (all ASCII)
                - Invalid: Text contains non-ASCII characters
        """
        if not input_text:
            return QtGui.QValidator.Acceptable

        # Check if all characters are ASCII (0-127)
        try:
            input_text.encode("ascii")
            return QtGui.QValidator.Acceptable
        except UnicodeEncodeError:
            return QtGui.QValidator.Invalid

    def fixup(self, input_text: str) -> str:
        """Fix invalid input by removing non-ASCII characters.

        Args:
            input_text (str): Input text to fix.

        Returns:
            str: Fixed text with only ASCII characters.
        """
        return "".join(c for c in input_text if ord(c) < 128)


class MayaNodeNameValidator(QtGui.QValidator):
    """Validator for Maya node names.

    Allows alphanumeric characters, underscores, colons, and pipes.
    Prevents Japanese and other non-ASCII characters.
    """

    def validate(self, input_text: str, pos: int) -> QtGui.QValidator.State:
        """Validate input text.

        Args:
            input_text (str): Text to validate.
            pos (int): Cursor position.

        Returns:
            QtGui.QValidator.State: Validation result.
                - Acceptable: Text is valid
                - Invalid: Text contains invalid characters
        """
        if not input_text:
            return QtGui.QValidator.Acceptable

        # Check if all characters are valid for Maya node names
        # Allow: alphanumeric, underscore, colon, pipe
        pattern = r"^[a-zA-Z0-9_:|]+$"
        if re.match(pattern, input_text):
            return QtGui.QValidator.Acceptable

        return QtGui.QValidator.Invalid

    def fixup(self, input_text: str) -> str:
        """Fix invalid input by removing invalid characters.

        Args:
            input_text (str): Input text to fix.

        Returns:
            str: Fixed text with only valid characters.
        """
        # Remove invalid characters using regex
        return re.sub(r"[^a-zA-Z0-9_:|]", "", input_text)


class MayaNodePatternValidator(QtGui.QValidator):
    """Validator for Maya node name patterns (with wildcards).

    Allows alphanumeric characters, underscores, colons, pipes,
    and wildcards (* and ?).
    Prevents Japanese and other non-ASCII characters.
    """

    def validate(self, input_text: str, pos: int) -> QtGui.QValidator.State:
        """Validate input text.

        Args:
            input_text (str): Text to validate.
            pos (int): Cursor position.

        Returns:
            QtGui.QValidator.State: Validation result.
                - Acceptable: Text is valid
                - Invalid: Text contains invalid characters
        """
        if not input_text:
            return QtGui.QValidator.Acceptable

        pattern = r"^[a-zA-Z0-9_:|*?]+$"
        if re.match(pattern, input_text):
            return QtGui.QValidator.Acceptable

        return QtGui.QValidator.Invalid

    def fixup(self, input_text: str) -> str:
        """Fix invalid input by removing invalid characters.

        Args:
            input_text (str): Input text to fix.

        Returns:
            str: Fixed text with only valid characters.
        """
        # Remove invalid characters using regex
        return re.sub(r"[^a-zA-Z0-9_:|*?]", "", input_text)
