/**
 * @file calculator.h
 * @brief Header file for Calculator operations.
 */

#ifndef CALCULATOR_H
#define CALCULATOR_H

/**
 * @brief Calculator structure for basic arithmetic operations.
 */
typedef struct {
    /** The current value stored in the calculator. */
    int value;
} Calculator;

Calculator* calculator_new(int initial_value);
void calculator_free(Calculator* calc);
int calculator_add(Calculator* calc, int x, int y);
int calculator_multiply(Calculator* calc, int x, int y);
double calculator_divide(Calculator* calc, double x, double y);
int calculator_calculate_expression(Calculator* calc, int x, int y, int z);
int helper_function(int* data, int length);

#endif /* CALCULATOR_H */
