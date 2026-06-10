namespace SampleProject;

/// <summary>
/// A simple calculator that performs basic arithmetic operations.
/// </summary>
/// <remarks>
/// This module provides basic arithmetic operations through the Calculator class.
/// </remarks>
public class Calculator
{
    /// <summary>
    /// The current value stored in the calculator.
    /// </summary>
    private int _value;

    /// <summary>
    /// Initialize calculator with an optional starting value.
    /// </summary>
    /// <param name="initialValue">The starting value (default: 0)</param>
    public Calculator(int initialValue = 0)
    {
        _value = initialValue;
    }

    /// <summary>
    /// Add two numbers and return the result.
    /// </summary>
    /// <param name="x">First number</param>
    /// <param name="y">Second number</param>
    /// <returns>Sum of x and y</returns>
    public int Add(int x, int y)
    {
        return x + y;
    }

    /// <summary>
    /// Multiply two numbers and return the result.
    /// </summary>
    /// <param name="x">First number</param>
    /// <param name="y">Second number</param>
    /// <returns>Product of x and y</returns>
    public int Multiply(int x, int y)
    {
        return x * y;
    }

    /// <summary>
    /// Divide x by y and return the result.
    /// </summary>
    /// <param name="x">Numerator</param>
    /// <param name="y">Denominator</param>
    /// <returns>Result of division</returns>
    public double Divide(double x, double y)
    {
        return x / y;
    }

    /// <summary>
    /// Private method (should be marked as private in index).
    /// </summary>
    private string PrivateMethod()
    {
        return "private";
    }

    /// <summary>
    /// Calculate a complex expression using multiple operations.
    /// </summary>
    /// <param name="x">First operand</param>
    /// <param name="y">Second operand</param>
    /// <param name="z">Third operand</param>
    /// <returns>Result of (x + y) * z</returns>
    public int CalculateExpression(int x, int y, int z)
    {
        var sumResult = Add(x, y);
        return Multiply(sumResult, z);
    }

    /// <summary>
    /// Top-level helper function to process data.
    /// </summary>
    /// <param name="data">Array of items</param>
    /// <returns>Length of the array</returns>
    public static int HelperFunction(int[] data)
    {
        return data.Length;
    }
}
