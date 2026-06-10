Namespace SampleProject
    ''' <summary>
    ''' A simple calculator that performs basic arithmetic operations.
    ''' </summary>
    ''' <remarks>
    ''' This module provides basic arithmetic operations through the Calculator class.
    ''' </remarks>
    Public Class Calculator
        ''' <summary>
        ''' The current value stored in the calculator.
        ''' </summary>
        Private _value As Integer

        ''' <summary>
        ''' Initialize calculator with an optional starting value.
        ''' </summary>
        ''' <param name="initialValue">The starting value (default: 0)</param>
        Public Sub New(Optional initialValue As Integer = 0)
            _value = initialValue
        End Sub

        ''' <summary>
        ''' Add two numbers and return the result.
        ''' </summary>
        ''' <param name="x">First number</param>
        ''' <param name="y">Second number</param>
        ''' <returns>Sum of x and y</returns>
        Public Function Add(x As Integer, y As Integer) As Integer
            Return x + y
        End Function

        ''' <summary>
        ''' Multiply two numbers and return the result.
        ''' </summary>
        ''' <param name="x">First number</param>
        ''' <param name="y">Second number</param>
        ''' <returns>Product of x and y</returns>
        Public Function Multiply(x As Integer, y As Integer) As Integer
            Return x * y
        End Function

        ''' <summary>
        ''' Divide x by y and return the result.
        ''' </summary>
        ''' <param name="x">Numerator</param>
        ''' <param name="y">Denominator</param>
        ''' <returns>Result of division</returns>
        Public Function Divide(x As Double, y As Double) As Double
            Return x / y
        End Function

        ''' <summary>
        ''' Private method (should be marked as private in index).
        ''' </summary>
        Private Function PrivateMethod() As String
            Return "private"
        End Function

        ''' <summary>
        ''' Calculate a complex expression using multiple operations.
        ''' </summary>
        ''' <param name="x">First operand</param>
        ''' <param name="y">Second operand</param>
        ''' <param name="z">Third operand</param>
        ''' <returns>Result of (x + y) * z</returns>
        Public Function CalculateExpression(x As Integer, y As Integer, z As Integer) As Integer
            Dim sumResult As Integer = Add(x, y)
            Return Multiply(sumResult, z)
        End Function

        ''' <summary>
        ''' Top-level helper function to process data.
        ''' </summary>
        ''' <param name="data">Array of items</param>
        ''' <returns>Length of the array</returns>
        Public Shared Function HelperFunction(data() As Integer) As Integer
            Return data.Length
        End Function
    End Class
End Namespace
