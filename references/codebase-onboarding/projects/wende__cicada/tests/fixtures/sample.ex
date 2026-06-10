defmodule Test do
  @moduledoc """
  A simple test module for parser validation.
  """

  def hello(name) do
    "Hello #{name}"
  end

  defp private_func do
    :ok
  end

  def multi_arity(a, b, c) do
    {a, b, c}
  end

  def no_params do
    :ok
  end

  defp another_private(x, y) do
    x + y
  end
end
