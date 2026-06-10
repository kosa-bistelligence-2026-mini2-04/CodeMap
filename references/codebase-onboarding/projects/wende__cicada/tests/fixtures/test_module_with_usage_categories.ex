defmodule AB do
  @moduledoc """
  Test module with all usage categories: aliases, imports, requires, uses, and value mentions.
  """

  # Aliases - multi-line alias block
  alias AB.{
    TypeParser,
    Generators
  }

  # Imports
  import ExUnit.Assertions

  # Uses
  use ExUnitProperties

  # Example function that uses TypeParser as a value (value mention)
  defdelegate get_function_spec(module, function_name), to: TypeParser

  def example_function do
    # This creates a value mention of Generators
    Generators
  end
end
