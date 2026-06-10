/**
 * A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through the Calculator class.
 */
class Calculator(private var value: Int = 0) {

  /**
   * Add two numbers and return the result.
   *
   * @param x First number
   * @param y Second number
   * @return Sum of x and y
   */
  def add(x: Int, y: Int): Int = {
    x + y
  }

  /**
   * Multiply two numbers and return the result.
   *
   * @param x First number
   * @param y Second number
   * @return Product of x and y
   */
  def multiply(x: Int, y: Int): Int = {
    x * y
  }

  /**
   * Divide x by y and return the result.
   *
   * @param x Numerator
   * @param y Denominator
   * @return Result of division
   */
  def divide(x: Double, y: Double): Double = {
    x / y
  }

  /**
   * Private method (should be marked as private in index).
   */
  private def privateMethod(): String = {
    "private"
  }

  /**
   * Calculate a complex expression using multiple operations.
   *
   * @param x First operand
   * @param y Second operand
   * @param z Third operand
   * @return Result of (x + y) * z
   */
  def calculateExpression(x: Int, y: Int, z: Int): Int = {
    val sumResult = add(x, y)
    multiply(sumResult, z)
  }
}

/**
 * Companion object for Calculator.
 */
object Calculator {

  /**
   * Top-level helper function to process data.
   *
   * @param data Sequence of items
   * @return Length of the sequence
   */
  def helperFunction(data: Seq[Int]): Int = {
    data.length
  }

  /**
   * Private function in companion object.
   */
  private def privateFunction(): Unit = {
    // Private implementation
  }
}
