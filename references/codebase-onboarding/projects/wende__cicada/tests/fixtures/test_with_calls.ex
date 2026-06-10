defmodule MyApp.UserService do
  @moduledoc """
  Service for user operations.
  """

  alias MyApp.{User, Post}
  alias MyApp.Database, as: DB

  @doc """
  Creates a new user.
  """
  def create_user(name, email) do
    user = User.new(name, email)
    DB.insert(user)
    Post.create_for_user(user)
    {:ok, user}
  end

  @doc """
  Finds a user by ID.
  """
  def find_user(id) do
    result = DB.get(id)
    User.validate(result)
  end

  defp validate_email(email) do
    String.contains?(email, "@")
  end

  def process_user(user) do
    validate_email(user.email)
    User.save(user)
  end
end
