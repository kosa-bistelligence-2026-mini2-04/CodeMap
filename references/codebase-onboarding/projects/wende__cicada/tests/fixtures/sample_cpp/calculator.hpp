/**
 * @file calculator.hpp
 * @brief Header file for Calculator class.
 */

#ifndef CALCULATOR_HPP
#define CALCULATOR_HPP

#include <string>
#include <vector>

namespace calculator {

/**
 * @brief A simple calculator that performs basic arithmetic operations.
 */
class Calculator {
public:
    /**
     * @brief Create a new calculator with an initial value.
     * @param initial_value The starting value (default: 0)
     */
    explicit Calculator(int initial_value = 0);

    /**
     * @brief Add two numbers and return the result.
     */
    int add(int x, int y) const;

    /**
     * @brief Multiply two numbers and return the result.
     */
    int multiply(int x, int y) const;

    /**
     * @brief Divide x by y and return the result.
     */
    double divide(double x, double y) const;

    /**
     * @brief Calculate a complex expression.
     */
    int calculateExpression(int x, int y, int z) const;

private:
    int value_;

    /**
     * @brief Private method.
     */
    std::string privateMethod() const;
};

/**
 * @brief Top-level helper function.
 */
size_t helperFunction(const std::vector<int>& data);

}  // namespace calculator

#endif  // CALCULATOR_HPP
