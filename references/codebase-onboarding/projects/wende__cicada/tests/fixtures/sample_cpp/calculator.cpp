/**
 * @file calculator.cpp
 * @brief A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through the Calculator class.
 */

#include "calculator.hpp"
#include <string>

namespace calculator {

/**
 * @brief Create a new calculator with an initial value.
 *
 * @param initial_value The starting value (default: 0)
 */
Calculator::Calculator(int initial_value) : value_(initial_value) {}

/**
 * @brief Add two numbers and return the result.
 *
 * @param x First number
 * @param y Second number
 * @return Sum of x and y
 */
int Calculator::add(int x, int y) const {
    return x + y;
}

/**
 * @brief Multiply two numbers and return the result.
 *
 * @param x First number
 * @param y Second number
 * @return Product of x and y
 */
int Calculator::multiply(int x, int y) const {
    return x * y;
}

/**
 * @brief Divide x by y and return the result.
 *
 * @param x Numerator
 * @param y Denominator
 * @return Result of division
 */
double Calculator::divide(double x, double y) const {
    if (y == 0) {
        return 0;
    }
    return x / y;
}

/**
 * @brief Private method (should be marked as private in index).
 */
std::string Calculator::privateMethod() const {
    return "private";
}

/**
 * @brief Calculate a complex expression using multiple operations.
 *
 * @param x First operand
 * @param y Second operand
 * @param z Third operand
 * @return Result of (x + y) * z
 */
int Calculator::calculateExpression(int x, int y, int z) const {
    int sumResult = add(x, y);
    return multiply(sumResult, z);
}

/**
 * @brief Top-level helper function to get vector size.
 *
 * @param data Vector of integers
 * @return Size of the vector
 */
size_t helperFunction(const std::vector<int>& data) {
    return data.size();
}

namespace {
/**
 * @brief Private function (anonymous namespace).
 */
void privateFunction() {
    // Private implementation
}
}  // namespace

}  // namespace calculator
