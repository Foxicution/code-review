import toml


def read_json(path):
    with open(path, 'r') as json_file:
        return json_file.read()


if __name__ == "__main__":
    output_file = ".streamlit/secrets.toml"

    config = {"db_key": read_json('secrets/code-review-84ddb-firebase-adminsdk-ysphl-460c783606.json'),
              "openai_key": read_json('secrets/openai_key.json'),
              'prompts': read_json('secrets/prompts.json')}

    toml_config = toml.dumps(config)

    with open(output_file, "w") as target:
        target.write(toml_config)
