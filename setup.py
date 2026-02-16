
from setuptools import setup, find_packages

setup(
    name='bravas',
    version='0.31.1',
    author= "Isaac, Andrea",
    author_email= "isaacleis.garrote@usc.es",
    description = 'Library to perform biorefinery and value chain assestment',  
    long_description = open("README.md").read(),
    long_description_content_type= "text/markdown",
    url = "https://github.com/Biogroup-USC/BRAVAS.git", 
    packages = find_packages(),
    include_package_data = True,
    package_data={
        "multimodelling.chems": ["database/Multimodelling_Chem.db"]
    },
    python_requires = '>=3.8, <3.13'  
)
