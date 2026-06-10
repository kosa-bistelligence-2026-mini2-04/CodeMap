defmodule MyApp.User do
  @moduledoc """
  User module.
  """

  def new(name, email) do
    %{name: name, email: email}
  end

  def validate(user) do
    {:ok, user}
  end

  def save(user) do
    {:ok, user}
  end
end

defmodule MyApp.Post do
  def create_for_user(user) do
    %{user_id: user.id, content: ""}
  end
end

defmodule MyApp.Database do
  def insert(data) do
    {:ok, data}
  end

  def get(id) do
    {:ok, %{id: id}}
  end
end
