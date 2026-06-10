# frozen_string_literal: true

# A simple calculator that performs basic arithmetic operations.
#
# This module provides basic arithmetic operations through the Calculator class.
class Calculator
  # The current value stored in the calculator.
  attr_accessor :value

  # Initialize calculator with an optional starting value.
  #
  # @param initial_value [Integer] The starting value (default: 0)
  def initialize(initial_value = 0)
    @value = initial_value
  end

  # Add two numbers and return the result.
  #
  # @param x [Integer] First number
  # @param y [Integer] Second number
  # @return [Integer] Sum of x and y
  def add(x, y)
    x + y
  end

  # Multiply two numbers and return the result.
  #
  # @param x [Integer] First number
  # @param y [Integer] Second number
  # @return [Integer] Product of x and y
  def multiply(x, y)
    x * y
  end

  # Divide x by y and return the result.
  #
  # @param x [Numeric] Numerator
  # @param y [Numeric] Denominator
  # @return [Float] Result of division
  def divide(x, y)
    x.to_f / y
  end

  # Calculate a complex expression using multiple operations.
  #
  # @param x [Integer] First operand
  # @param y [Integer] Second operand
  # @param z [Integer] Third operand
  # @return [Integer] Result of (x + y) * z
  def calculate_expression(x, y, z)
    sum_result = add(x, y)
    multiply(sum_result, z)
  end

  private

  # Private method (should be marked as private in index).
  #
  # @return [String] A private string
  def private_method
    'private'
  end
end

# Top-level helper function to process data.
#
# @param data [Array] Array of items
# @return [Integer] Length of the array
def helper_function(data)
  data.length
end

# Private function at module level.
def private_function
  # Private implementation
end

private :private_function
