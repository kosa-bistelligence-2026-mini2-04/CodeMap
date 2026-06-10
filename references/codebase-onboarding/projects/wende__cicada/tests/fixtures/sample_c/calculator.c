/**
 * @file calculator.c
 * @brief A simple calculator that performs basic arithmetic operations.
 *
 * This module provides basic arithmetic operations through Calculator functions.
 */

#include "calculator.h"
#include <stdlib.h>

/**
 * @brief Create a new calculator with an initial value.
 *
 * @param initial_value The starting value
 * @return Pointer to the new Calculator
 */
Calculator* calculator_new(int initial_value) {
    Calculator* calc = (Calculator*)malloc(sizeof(Calculator));
    if (calc) {
        calc->value = initial_value;
    }
    return calc;
}

/**
 * @brief Free calculator memory.
 *
 * @param calc Pointer to the calculator to free
 */
void calculator_free(Calculator* calc) {
    free(calc);
}

/**
 * @brief Add two numbers and return the result.
 *
 * @param calc Pointer to the calculator
 * @param x First number
 * @param y Second number
 * @return Sum of x and y
 */
int calculator_add(Calculator* calc, int x, int y) {
    return x + y;
}

/**
 * @brief Multiply two numbers and return the result.
 *
 * @param calc Pointer to the calculator
 * @param x First number
 * @param y Second number
 * @return Product of x and y
 */
int calculator_multiply(Calculator* calc, int x, int y) {
    return x * y;
}

/**
 * @brief Divide x by y and return the result.
 *
 * @param calc Pointer to the calculator
 * @param x Numerator
 * @param y Denominator
 * @return Result of division, or 0 if y is 0
 */
double calculator_divide(Calculator* calc, double x, double y) {
    if (y == 0) {
        return 0;
    }
    return x / y;
}

/**
 * @brief Calculate a complex expression using multiple operations.
 *
 * @param calc Pointer to the calculator
 * @param x First operand
 * @param y Second operand
 * @param z Third operand
 * @return Result of (x + y) * z
 */
int calculator_calculate_expression(Calculator* calc, int x, int y, int z) {
    int sum_result = calculator_add(calc, x, y);
    return calculator_multiply(calc, sum_result, z);
}

/**
 * @brief Private helper function (static, not exported).
 */
static const char* private_method(void) {
    return "private";
}

/**
 * @brief Top-level helper function to get array length.
 *
 * @param data Array of integers
 * @param length Length of the array
 * @return The length parameter
 */
int helper_function(int* data, int length) {
    return length;
}
