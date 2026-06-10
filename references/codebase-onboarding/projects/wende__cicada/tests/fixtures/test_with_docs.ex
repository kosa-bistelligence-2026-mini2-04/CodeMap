defmodule UserManager do
  @moduledoc """
  Module for managing user operations.
  """

  @doc """
  Creates a new user with the given name and email.
  Returns {:ok, user} on success or {:error, reason} on failure.
  """
  @spec create_user(String.t(), String.t()) :: {:ok, map()} | {:error, atom()}
  def create_user(name, email) do
    user = %{name: name, email: email, id: generate_id()}
    {:ok, user}
  end

  @doc """
  Finds a user by their ID.
  """
  @spec find_user(integer()) :: {:ok, map()} | {:error, :not_found}
  def find_user(id) do
    # Mock implementation
    {:error, :not_found}
  end

  @doc """
  Updates a user's email address.
  """
  def update_email(user_id, new_email) do
    {:ok, %{id: user_id, email: new_email}}
  end

  @spec generate_id() :: integer()
  defp generate_id do
    :rand.uniform(1000000)
  end

  defp validate_email(email) do
    String.contains?(email, "@")
  end
end
