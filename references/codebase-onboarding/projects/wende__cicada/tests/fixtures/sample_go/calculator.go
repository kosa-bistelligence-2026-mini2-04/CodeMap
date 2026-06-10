// Package calculator provides basic arithmetic operations.
//
// This module provides basic arithmetic operations through the Calculator struct.
package calculator

// Calculator is a simple calculator that performs basic arithmetic operations.
type Calculator struct {
	// Value is the current value stored in the calculator.
	Value int
}

// New creates a new calculator with an optional starting value.
func New(initialValue int) *Calculator {
	return &Calculator{Value: initialValue}
}

// Add adds two numbers and returns the result.
//
// Parameters:
//   - x: First number
//   - y: Second number
//
// Returns:
//   Sum of x and y
func (c *Calculator) Add(x, y int) int {
	return x + y
}

// Multiply multiplies two numbers and returns the result.
//
// Parameters:
//   - x: First number
//   - y: Second number
//
// Returns:
//   Product of x and y
func (c *Calculator) Multiply(x, y int) int {
	return x * y
}

// Divide divides x by y and returns the result.
// Returns 0 if y is zero.
//
// Parameters:
//   - x: Numerator
//   - y: Denominator
//
// Returns:
//   Result of division
func (c *Calculator) Divide(x, y float64) float64 {
	if y == 0 {
		return 0
	}
	return x / y
}

// privateMethod is a private method (should be marked as private in index).
func (c *Calculator) privateMethod() string {
	return "private"
}

// CalculateExpression calculates a complex expression using multiple operations.
//
// Parameters:
//   - x: First operand
//   - y: Second operand
//   - z: Third operand
//
// Returns:
//   Result of (x + y) * z
func (c *Calculator) CalculateExpression(x, y, z int) int {
	sumResult := c.Add(x, y)
	return c.Multiply(sumResult, z)
}

// HelperFunction is a top-level function to process data.
//
// Parameters:
//   - data: Slice of items
//
// Returns:
//   Length of the slice
func HelperFunction(data []int) int {
	return len(data)
}

// privateFunction is a private function (lowercase).
func privateFunction() {
	// Private implementation
}
