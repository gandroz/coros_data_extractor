# COROS data extractor from Training Hub

I love my Coros watch and the training hub is very helpful, but I also like data and I want to do further analysis with my own data. Coros does not provide official API to access you data, however the training hub has a public API you can interact with.

This simple tool helps you extract some of your data. For example, I've used this tool to extract all my runs with a meaningful title, always the same training, so that I can track my performance over time. I was then able to see the impact of my training on my heart rate, which is very encouraging.

## Usage

### Data extraction

You first need to setup two environment variables

```bash
EMAIL="...@.."
PASSWORD="....."
```

Then the tool is very easy to use with those simple commands:

```python
from coros_data_extractor.data import CorosDataExtractor

extractor = CorosDataExtractor()
extractor.login(os.environ.get("EMAIL"), os.environ.get("PASSWORD"))
extractor.extract_data()
extractor.to_json()
```

And that's it ! You now have your extracted data in a JSON file.

### Data models

For a more user friendly manipulation of the data, extraction of the data results is represented by a [pydantic](https://docs.pydantic.dev/latest/) data model. The model is described in `coros_data_extractor.model` module, but essentially you will find a list of activities with the description of the activity, the laps, and the associated time series.
