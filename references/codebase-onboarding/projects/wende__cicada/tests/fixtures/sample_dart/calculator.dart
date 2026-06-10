/// A simple calculator that performs basic arithmetic operations.
///
/// This module provides basic arithmetic operations through the Calculator class.
class Calculator {
  /// The current value stored in the calculator.
  int _value;

  /// Initialize calculator with an optional starting value.
  ///
  /// [initialValue] is the starting value (default: 0).
  Calculator([int initialValue = 0]) : _value = initialValue;

  /// Add two numbers and return the result.
  ///
  /// [x] is the first number.
  /// [y] is the second number.
  /// Returns the sum of x and y.
  int add(int x, int y) {
    return x + y;
  }

  /// Multiply two numbers and return the result.
  ///
  /// [x] is the first number.
  /// [y] is the second number.
  /// Returns the product of x and y.
  int multiply(int x, int y) {
    return x * y;
  }

  /// Divide x by y and return the result.
  ///
  /// [x] is the numerator.
  /// [y] is the denominator.
  /// Returns the result of division.
  double divide(double x, double y) {
    return x / y;
  }

  /// Private method (should be marked as private in index).
  String _privateMethod() {
    return 'private';
  }

  /// Calculate a complex expression using multiple operations.
  ///
  /// [x] is the first operand.
  /// [y] is the second operand.
  /// [z] is the third operand.
  /// Returns the result of (x + y) * z.
  int calculateExpression(int x, int y, int z) {
    final sumResult = add(x, y);
    return multiply(sumResult, z);
  }
}

/// Top-level helper function to process data.
///
/// [data] is the list of items.
/// Returns the length of the list.
int helperFunction(List<int> data) {
  return data.length;
}

/// Private function (prefixed with underscore).
void _privateFunction() {
  // Private implementation
}
